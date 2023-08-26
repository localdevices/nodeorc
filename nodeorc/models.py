import json
import logging
import os
import requests
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, AnyHttpUrl, ConfigDict
from pyorc import service
from io import BytesIO
# nodeodm specific imports
from nodeorc import callbacks, utils
from urllib.parse import urljoin


class Callback(BaseModel):
    func_name: Optional[str] = "post_discharge"  # name of function that establishes the callback json
    kwargs: Optional[Dict[str, Any]] = {}
    callback_endpoint: Optional[str] = "/example"  # used to extend the default callback url

    @validator("func_name")
    def name_in_callbacks(cls, v):
        if not(hasattr(callbacks, v)):
            raise ValueError(f"callback {v} not available in callbacks")
        return v


class CallbackUrl(BaseModel):
    """
    Definition of accessibility to storage and callback locations
    """
    url: AnyHttpUrl = "https://127.0.0.1:8000/api"
    token: Optional[str] = "abcdefgh"

    @validator("url")
    def validate_url(cls, v):
        try:
            r = requests.get(
                v,
            )
        except requests.exceptions.ConnectionError as e:
            raise ValueError(f"Maximum retries on connection {v} reached")
        return v


class Storage(BaseModel):
    endpoint_url: AnyHttpUrl = "http://127.0.0.1:9000"
    aws_access_key_id: str = "admin"
    aws_secret_access_key: str = "password"
    bucket_name: str = "video"

    @property
    def bucket(self):
        return utils.get_bucket(
            endpoint_url=str(self.endpoint_url),
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            bucket_name=self.bucket_name,
        )
    def upload_io(self, obj, dest, **kwargs):
        utils.upload_file(obj, self.bucket, dest=dest, **kwargs)

class File(BaseModel):
    """
    Definition of the location, naming of raw result on tmp location, and in/output file name for cloud storage
    """
    remote_name: str = "video.mp4"
    tmp_name: str = "video.mp4"


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

    @validator("name")
    def name_in_service(cls, v):
        if not(hasattr(service, v)):
            raise ValueError(f"task {v} not available in pyorc.service")
        return v

    def execute(self, storage=None, tmp=".", base_url="http://localhost:8000", logger=logging):
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
        if self.callback is not None:
            self.execute_callback(base_url, tmp=tmp)


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
        for k, v in self.output_files.items():
            tmp_file = os.path.join(tmp, v.tmp_name)
            # check if file is present
            if not(os.path.isfile(tmp_file)):
                raise FileNotFoundError(f"Temporary file {tmp_file} was not created by subtask")
            with open(tmp_file, "rb") as f:
                obj = BytesIO(f.read())
            obj.seek(0)
            storage.upload_io(obj, dest=v.remote_name)


    def execute_callback(self, base_url, tmp):
        # get the name of callback
        func = getattr(callbacks, self.callback.func_name)
        # call the callback function with the output files as input, this is a standardized approach
        msg = func(self.output_files, tmp=tmp)
        url = urljoin(str(base_url), self.callback.callback_endpoint)
        # perform callback
        requests.post(url, json=msg) #json.dumps(msg))




class Task(BaseModel):
    """
    Definition of an entire task
    """
    id: str = str(uuid.uuid4())
    time: datetime = datetime.now()
    callback_url: CallbackUrl
    callback_endpoint_error: str = "/processing/examplevideo/error"
    callback_endpoint_complete: str = "/processing/examplevideo/complete"
    storage: Optional[Storage] = None
    subtasks: Optional[List[Subtask]] = []
    input_files: Optional[List[File]] = []  # files that are needed to perform any subtask
    logger: logging.Logger = logging

    class Config:
        arbitrary_types_allowed = True


    def execute(self, tmp):
        """
        Execute the entire task logic

        Parameters
        ----------
        tmp

        Returns
        -------

        """
        # prepare tmp location
        if not(os.path.isdir(tmp)):
            os.makedirs(tmp)
        # first download the input files
        try:
            self.logger.info(f"Performing task defined at {self.time} with id {self.id}")
            self.logger.info(f"Downloading all inputs to {tmp}")
            self.download_input(tmp)
            # then perform all subtasks in order, upload occur within the subtasks
            self.logger.info(f"Executing subtasks")
            self.execute_subtasks(tmp)
            self.logger.info(f"Removing temporary files")
            r = self.callback_complete(msg=f"Task complete, id: {str(self.id)}")
            # clean up the temp location
            shutil.rmtree(tmp)
        except BaseException as e:
            r = self.callback_error(msg=str(e))
        if r.status_code == 200:
            self.logger.info(f"Task id {str(self.id)} completed")
        else:
            self.logger.error(f"Task id {str(self.id)} failed with code {r.status_code}")
            raise Exception("Error detected, restarting node")

    def download_input(self, tmp):
        """
        Downloads all required inputs to a required temp path

        Parameters
        ----------
        tmp : str
            path to temporary local file store

        """
        for file in self.input_files:
            trg = os.path.join(tmp, file.tmp_name)
            # put the input file on tmp location
            self.storage.bucket.download_file(file.remote_name, trg)


    def execute_subtasks(self, tmp):
        """

        Parameters
        ----------
        tmp : str
            path to temporary local file store

        """
        for subtask in self.subtasks:
            # execute the subtask, ensuring that the storage and bucket are known
            subtask.execute(storage=self.storage, tmp=tmp, base_url=self.callback_url.url, logger=self.logger)

    def callback_error(self, msg):
        """
        Perform callback in case an error is received

        Parameters
        ----------
        msg : str
            message to pass

        Returns
        -------

        r : requests.response
        """
        url = urljoin(str(self.callback_url.url), self.callback_endpoint_error)
        r = requests.post(
            url,
            json={
                "error": msg
            }
        )
        return r

    def callback_complete(self, msg):
        url = urljoin(str(self.callback_url.url), self.callback_endpoint_complete)
        r = requests.post(
            url,
            json={
                "msg": msg
            }
        )
        return r
