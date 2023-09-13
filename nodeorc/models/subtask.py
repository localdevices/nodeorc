import logging
import os
import requests
from typing import Optional, Dict
from pydantic import field_validator, BaseModel
from pyorc import service
from io import BytesIO
from urllib.parse import urljoin

# nodeodm specific imports
from nodeorc import callbacks
from . import Callback
from . import File

class Subtask(BaseModel):
    """
    Definition of a subtask with its keyword arguments (connects to pyorc.service level)
    """

    name: str = "VelocityFlowProcessor"  # name of subtask to perform (see pyorc.service)
    kwargs: Dict = {}  # keyword args used for subtask
    # these files are added as filled in after download in the kwargs
    callback: Optional[Callback] = None  # callbacks for the subtask (can be multiple)
    # for files, if key names are in kwargs, then within task handling these can be replaced
    # expected input files (relative to .tmp location) used as input
    input_files: Optional[Dict[str, File]] = {}
    # files that are produced from the subtask (relative to .tmp location) and remote location
    output_files: Optional[Dict[str, File]] = {}

    @field_validator("name")
    @classmethod
    def name_in_service(cls, v):
        if not(hasattr(service, v)):
            raise ValueError(f"task {v} not available in pyorc.service")
        return v

    def execute(self, timestamp=None, storage=None, tmp=".", callback_url=None, logger=logging):
        """
        Execute the subtask and return outputs to defined storage (if provided)

        Parameters
        ----------
        storage : Storage,
            the Storage object that should be used to return data to.

        """
        # replace or add kwargs with filename args
        self.replace_kwargs_files(tmp=tmp)
        self.execute_subtask(logger=logger)
        if storage is not None:
            self.upload_outputs(storage, tmp)
        if self.callback and callback_url:
            self.execute_callback(callback_url, timestamp=timestamp, tmp=tmp)

    def replace_files(self, input_files, output_files):
        """
        replace the mock files of inputs and outputs with the actual files as defined in main task

        Parameters
        ----------
        input_files : Dict[str, File]
            Input files as defined on main task level
        output_files : Dict[str, File]
            Output files as defined on main task level

        Returns
        -------

        """
        for k, v in input_files.items():
            if k in self.input_files:
                self.input_files[k] = v
        for k, v in output_files.items():
            if k in self.output_files:
                self.output_files[k] = v


    def replace_kwargs_files(self, tmp="."):
        # replace only when the keyname is in kwargs
        for k, v in self.input_files.items():
            if k in self.kwargs:
                self.kwargs[k] = os.path.join(tmp, v.tmp_name)
        for k, v in self.output_files.items():
            if k in self.kwargs:
                self.kwargs[k] = os.path.join(tmp, v.tmp_name)


    def execute_subtask(self, logger=logging):
        """
        Execute subtask

        Returns
        -------

        """
        # retrieve task name from pyorc service level
        logger.info(f"Executing task {self.name}")
        task_func = getattr(service, self.name)
        task_func(**self.kwargs, logger=logger)

    def upload_outputs(self, storage, tmp):
        """
        Uploads results from subtask to bucket identified in storage

        Parameters
        ----------
        storage : Storage
            referring to bucket where results should be posted
        tmp : temporary file location where outputs are expected

        Returns
        -------

        """
        for k, v in self.output_files.items():
            # if remote name is None, then upload will be skipped entirely
            if v.remote_name:
                tmp_file = os.path.join(tmp, v.tmp_name)
                # check if file is present
                if not(os.path.isfile(tmp_file)):
                    raise FileNotFoundError(f"Temporary file {tmp_file} was not created by subtask")
                with open(tmp_file, "rb") as f:
                    obj = BytesIO(f.read())
                obj.seek(0)
                storage.upload_io(obj, dest=v.remote_name)


    def execute_callback(self, callback_url, timestamp, tmp):
        # get the name of callback
        func = getattr(callbacks, self.callback.func_name)
        # get the type of request. Typically this is POST for an entirely new time series record created from an edge
        # device, and PATCH for an existing record that must be provided with analyzed flows
        request = getattr(
            requests,
            self.callback.request_type.lower()
        )
        # call the callback function with the output files as input, this is a standardized approach
        # prepare headers with the token
        if callback_url.token:
            headers = {"Authorization": f"Bearer {callback_url.token}"}
        else:
            headers = {}
        msg = func(self.output_files, timestamp=timestamp, tmp=tmp)
        url = urljoin(str(callback_url.url), self.callback.endpoint)
        # perform callback (arrange the adding of token)
        r = request(
            url,
            json=msg,
            headers=headers
        )
        if r.status_code != 200:
            raise ValueError(f"callback to {url} failed with error code {r.status_code} and body {r.json()}")

