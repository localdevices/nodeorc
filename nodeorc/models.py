import json
import logging
import os
import requests
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, AnyStr
from pydantic import field_validator, BaseModel, AnyHttpUrl, ConfigDict, model_validator
from pyorc import service
from io import BytesIO
# nodeodm specific imports
from nodeorc import callbacks, utils
from urllib.parse import urljoin

failed_path = os.getenv("FAILED_PATH")
success_path = os.getenv("SUCCESS_PATH")

class Callback(BaseModel):
    func_name: Optional[str] = "discharge"  # name of function that establishes the callback json
    request_type: str = "POST"
    kwargs: Optional[Dict[str, Any]] = {}
    endpoint: Optional[str] = "/api/timeseries/"  # used to extend the default callback url

    @field_validator("func_name")
    @classmethod
    def name_in_callbacks(cls, v):
        if not(hasattr(callbacks, v)):
            raise ValueError(f"callback {v} not available in callbacks")
        return v



class CallbackUrl(BaseModel):
    """
    Definition of accessibility to storage and callback locations
    """
    url: AnyHttpUrl = "https://127.0.0.1:8000/api"
    token_refresh_end_point: Optional[str] = "/token/refresh"
    refresh_token: Optional[str] = None
    token: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        try:
            r = requests.get(
                v,
            )
        except requests.exceptions.ConnectionError as e:
            raise ValueError(f"Maximum retries on connection {v} reached")
        return v

    @model_validator(mode="after")
    def replace_token(self):
        """
        Checks if the token has expired, and replaces it upon creating this instance

        Returns
        -------

        """
        if self.refresh_token:
            # ensure you have a fresh token before continuing
            url = self.url + self.token_refresh_endpoint
            body = {"refresh": self.refresh_token}
            r = requests.post(url, json=body)
            self.token = r.json()["access"]


class Storage(BaseModel):
    url: str = "./tmp"
    bucket_name: str = "video"

    @property
    def bucket(self):
        return os.path.join(self.url, self.bucket_name)

    @property
    def delete(self):
        shutil.rmtree(self.bucket)

    def upload_io(self, obj, dest):
        """
        Upload a BytesIO object to a file on storage location

        Parameters
        ----------
        obj : io.BytesIO
            bytes to be written to file
        dest : str
            destination filename (only name, full path is formed from self.bucket)

        Returns
        -------

        """
        obj.seek(0)
        fn = os.path.join(self.bucket, dest)
        path = os.path.split(fn)[0]
        if not(os.path.isdir(path)):
            os.makedirs(path)
        # create file
        with open(fn, "wb") as f:
            f.write(obj.read())

    def download_file(self, filename, trg):
        """
        Download file from one local location to another target file (entire path inc. filename)

        Parameters
        ----------
        filename : str
            file within local bucket

        trg : file as it should be named locally

        Returns
        -------

        """
        shutil.copyfile(
            os.path.join(self.bucket, filename),
            trg
        )

class S3Storage(Storage):
    url: AnyHttpUrl = "http://127.0.0.1:9000"
    options: Dict[str, Any]


    @property
    def bucket(self):
        return utils.get_bucket(
            url=str(self.url),
            bucket_name=self.bucket_name,
            **self.options
        )

    def upload_io(self, obj, dest, **kwargs):
        utils.upload_io(obj, self.bucket, dest=dest, **kwargs)

    def download_file(self, filename, trg):
        """
        Download file from bucket to specified target file (entire path inc. filename)

        Parameters
        ----------
        filename : str
            file within bucket

        trg : file as it should be named locally

        Returns
        -------

        """
        self.bucket.download_file(filename, trg)



class File(BaseModel):
    """
    Definition of the location, naming of raw result on tmp location, and in/output file name for cloud storage
    """
    remote_name: str = "video.mp4"
    tmp_name: str = "video.mp4"

    def move(self, src, trg):
        """
        Moves the file from src folder to trg folder

        Parameters
        ----------
        src : str
            Source folder, where File is expected as tmp file
        trg :
            Target folder, where File must be moved to

        Returns
        -------

        """
        src_fn = os.path.join(src, self.tmp_name)
        trg_fn = os.path.join(trg, self.tmp_name)
        os.rename(src_fn, trg_fn)

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

    def execute(self, storage=None, tmp=".", callback_url=None, logger=logging):
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
            self.execute_callback(callback_url, tmp=tmp)


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
            tmp_file = os.path.join(tmp, v.tmp_name)
            # check if file is present
            if not(os.path.isfile(tmp_file)):
                raise FileNotFoundError(f"Temporary file {tmp_file} was not created by subtask")
            with open(tmp_file, "rb") as f:
                obj = BytesIO(f.read())
            obj.seek(0)
            storage.upload_io(obj, dest=v.remote_name)


    def execute_callback(self, callback_url, tmp):
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
        msg = func(self.output_files, tmp=tmp)
        url = urljoin(str(callback_url.url), self.callback.endpoint)
        # perform callback (arrange the adding of token)
        request(
            url,
            json=msg,
            headers=headers
        ) #json.dumps(msg))





class Task(BaseModel):
    """
    Definition of an entire task
    """
    id: str = str(uuid.uuid4())
    time: datetime = datetime.now()
    callback_url: Optional[Any] = None
    callback_endpoint_error: str = "/processing/examplevideo/error"
    callback_endpoint_complete: str = "/processing/examplevideo/complete"
    storage: Optional[Storage] = None
    subtasks: Optional[List[Subtask]] = []
    input_files: Optional[List[File]] = []  # files that are needed to perform any subtask
    logger: logging.Logger = logging
    model_config = ConfigDict(arbitrary_types_allowed=True)


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
            r = self.callback_complete(msg=f"Task complete, id: {str(self.id)}")
            # if the video was treated successfully, then we may move it to a location of interest if wanted
            if success_path:
                # move the video
                [input_file.move(tmp, success_path) for input_file in self.input_files]

        except BaseException as e:
            r = self.callback_error(msg=str(e))
            if failed_path:
                # we move the non-succeeded video to a separate path for inspection
                [input_file.move(tmp, failed_path) for input_file in self.input_files]

        # clean up the temp location
        self.logger.info(f"Removing temporary files")
        shutil.rmtree(tmp)

        # report success or error
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
            self.storage.download_file(file.remote_name, trg)
            # self.storage.bucket.download_file(file.remote_name, trg)


    def execute_subtasks(self, tmp):
        """

        Parameters
        ----------
        tmp : str
            path to temporary local file store

        """
        for subtask in self.subtasks:
            # execute the subtask, ensuring that the storage and bucket are known
            subtask.execute(storage=self.storage, tmp=tmp, callback_url=self.callback_url, logger=self.logger)

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
