import os
import boto3

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, HttpUrl
from pyorc import service

# nodeodm specific imports
import callbacks

class Callback(BaseModel):
    func_name: Optional[str] = "get_discharge"  # name of function that establishes the callback json
    kwargs: Optional[Dict[str, Any]] = {}
    url_subpath: Optional[HttpUrl] = "http://localhost:8000/api"  # used to extend the default callback url

    @validator("func_name")
    def name_in_callbacks(cls, v):
        if not(hasattr(callbacks, v)):
            raise NameError(f"callback {v} not available in callbacks")
        return v

class InputFile(BaseModel):
    """
    Definition of the location, naming of raw result on tmp location, and output file name for cloud storage per subtask
    """
    remote_name: str = "video.mp4"
    tmp_name = "video.mp4"


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
            raise NameError(f"task {v} not available in pyorc.service")
        return v
class CallbackUrl(BaseModel):
    """
    Definition of accessibility to storage and callback locations
    """
    callback_url: HttpUrl = "https://localhost:8000/api"
    callback_token: str = "abcdefgh"


class Storage(BaseModel):
    storage_url: HttpUrl = "http://127.0.0.1:9000"
    storage_user: str = "admin"
    storage_password: str = "password"
    storage_bucket: str = "video"

    @property
    def bucket(self):
        return boto3.resource(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_ACCESS_SECRET"),
            config=boto3.session.Config(signature_version="s3v4"),
        )

class Task(BaseModel):
    """
    Definition of an entire task
    """
    time: datetime = datetime.now()
    callback_url: CallbackUrl = None
    storage: Storage = None
    subtasks: Optional[List[Subtask]] = []
    input_files: Optional[InputFile] = []  # files that are needed to perform any subtask
