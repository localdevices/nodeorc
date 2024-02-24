import logging
import os
import requests
from typing import Optional, Dict, List
from pydantic import field_validator, BaseModel
from pyorc import service
from io import BytesIO

# nodeodm specific imports
from . import Callback
from . import File

class Subtask(BaseModel):
    """
    Definition of a subtask with its keyword arguments (connects to pyorc.service level)
    """

    name: str = "VelocityFlowProcessor"  # name of subtask to perform (see pyorc.service)
    kwargs: Dict = {}  # keyword args used for subtask
    # these files are added as filled in after download in the kwargs
    callbacks: Optional[List[Callback]] = None  # callbacks for the subtask (can be multiple)
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

    def execute(self, task, tmp=".", logger=logging): #timestamp=None, storage=None, tmp=".", taskcallback_url=None, logger=logging):
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
        if task.storage is not None:
            self.upload_outputs(task.storage, tmp)
        # if self.callbacks and task.callback_url:
        #     self.execute_callbacks(task, tmp=tmp) # task.callback_url, timestamp=task.timestamp, tmp=tmp)

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
