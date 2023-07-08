import os
import boto3
import requests

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, HttpUrl, ValidationError
from pyorc import service

# nodeodm specific imports
import callbacks
import utils

class Callback(BaseModel):
    func_name: Optional[str] = "get_discharge"  # name of function that establishes the callback json
    kwargs: Optional[Dict[str, Any]] = {}
    url_subpath: Optional[HttpUrl] = "http://localhost:8000/api"  # used to extend the default callback url

    @validator("func_name")
    def name_in_callbacks(cls, v):
        if not(hasattr(callbacks, v)):
            raise ValueError(f"callback {v} not available in callbacks")
        return v

class InputFile(BaseModel):
    """
    Definition of the location, naming of raw result on tmp location, and output file name for cloud storage per subtask
    """
    remote_name: str = "video.mp4"
    tmp_name: str = "video.mp4"


class OutputFile(BaseModel):
    """
    Definition of the location, naming of raw result on tmp location, and output file name for cloud storage per subtask
    """
    remote_name: str = "piv.nc"
    tmp_name: str = "OUTPUT/piv.nc"



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
    input_files: Optional[Dict[str, InputFile]] = {}
    # files that are produced from the subtask (relative to .tmp location) and remote location
    output_files: Optional[Dict[str, OutputFile]] = {}

    @validator("name")
    def name_in_service(cls, v):
        if not(hasattr(service, v)):
            raise ValueError(f"task {v} not available in pyorc.service")
        return v
class CallbackUrl(BaseModel):
    """
    Definition of accessibility to storage and callback locations
    """
    url: HttpUrl = "https://localhost:8000/api"
    token: str = "abcdefgh"

    @validator("url")
    def validate_url(cls, v):
        try:
            r = requests.get(
                v,
            )
        except requests.exceptions.ConnectionError as e:
            raise ValueError(f"Maximum retries on connection {v} reached")
        if r.status_code == 200:
            return v
        else:
            raise ValueError(f"Connection failed with status code {r.status_code}")


class Storage(BaseModel):
    endpoint_url: HttpUrl = "http://127.0.0.1:9000"
    aws_access_key_id: str = "admin"
    aws_secret_access_key: str = "password"
    bucket_name: str = "video"

    @property
    def bucket(self):
        return utils.get_bucket(
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            bucket_name=self.bucket_name,
        )


class Task(BaseModel):
    """
    Definition of an entire task
    """
    time: datetime = datetime.now()
    callback_url: CallbackUrl = None
    storage: Optional[Storage] = None
    subtasks: Optional[List[Subtask]] = []
    input_files: Optional[InputFile] = []  # files that are needed to perform any subtask
