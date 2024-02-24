import copy
import logging
import os
import requests
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, ConfigDict, model_validator, Field
from urllib.parse import urljoin

# nodeodm specific imports
from . import CallbackUrl, Storage, S3Storage, File, Subtask, Callback, REMOVE_FOR_TEMPLATE

class Task(BaseModel):
    """
    Definition of an entire task
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = datetime.now()
    callback_url: Optional[CallbackUrl] = None
    callback_endpoint_error: str = "/processing/examplevideo/error"
    callback_endpoint_complete: str = "/processing/examplevideo/complete"
    storage: Optional[Union[S3Storage, Storage]] = None
    subtasks: Optional[List[Subtask]] = []
    input_files: Optional[Dict[str, File]] = {}  # files that are needed to perform any subtask
    # files that are produced from the subtask (relative to .tmp location) and remote location
    output_files: Optional[Dict[str, File]] = {}
    callbacks: Optional[List[Callback]] = None
    logger: logging.Logger = logging
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def replace_subtask_files(self) -> 'Task':
        """
        Checks if the token has expired, and replaces it upon creating this instance

        Returns
        -------

        """
        # replace any inputs / outputs of subtasks (which may be mocks) with inputs / outputs defined in main task
        for subtask in self.subtasks:
            subtask.replace_files(self.input_files, self.output_files)
        return self



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
            self.logger.info(f"Performing task defined at {self.timestamp} with id {self.id}")
            self.logger.info(f"Downloading all inputs to {tmp}")
            self.download_input(tmp)
            # then perform all subtasks in order, upload occur within the subtasks
            self.logger.info(f"Executing subtasks")
            self.execute_subtasks(tmp, timestamp=self.timestamp)
            # r = self.callback_complete(msg=f"Task complete, id: {str(self.id)}")
            self.logger.info(f"Task id {str(self.id)} completed")
        except BaseException as e:
            # r = self.callback_error(msg=str(e))
            msg = f"Error in processing of subtask {str(self.id)}. Reason: {str(e)}"
            self.logger.error(msg)
            raise Exception(msg)
        # # clean up the temp location
        # self.logger.info(f"Removing temporary files")
        # shutil.rmtree(tmp)

        # report success or error
        # if r.status_code == 200:
        # else:
        #     self.logger.error(f"Task id {str(self.id)} failed with code {r.status_code} and message {r.json()}")
        #     raise Exception("Error detected, restarting node")

    def download_input(self, tmp):
        """
        Downloads all required inputs to a required temp path

        Parameters
        ----------
        tmp : str
            path to temporary local file store

        """
        for key, file in self.input_files.items():
            trg = os.path.join(tmp, file.tmp_name)
            # put the input file on tmp location
            self.storage.download_file(file.remote_name, trg)
            # self.storage.bucket.download_file(file.remote_name, trg)


    def execute_subtasks(self, tmp, timestamp=None):
        """

        Parameters
        ----------
        tmp : str
            path to temporary local file store

        """
        for subtask in self.subtasks:
            # execute the subtask, ensuring that the storage and bucket are known
            subtask.execute(
                # timestamp=timestamp,
                # storage=self.storage,
                tmp=tmp,
                task=self,
                # callback_url=self.callback_url,
                logger=self.logger
            )

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

    def to_file(self, fn, indent=4, **kwargs):
        with open(fn, "w") as f:
            f.write(self.to_json(indent=4, **kwargs))

    def to_json(self, indent=4, template=False, serialize=True):
        """
        Write task to fully serializable json format

        Parameters
        ----------
        indent : int
            indentation of json string (typically only used for
        template :
            write as template instead of full task. This means that dynamic fields are removed before writing.
            These fields are: id, time, input_files, :

        Returns
        -------

        """
        # make a copy of self before tampering with it
        task_copy = self.copy()
        if hasattr(self, "logger"):
            # remove the logger object which is not serializable
            delattr(task_copy, "logger")
        if template:
            # save as a template, so remove all dynamic items such as id, input files and time
            for attr in REMOVE_FOR_TEMPLATE:
                delattr(task_copy, attr)
        if serialize:
            task_json = task_copy.model_dump_json(indent=indent)
        else:
            task_json = task_copy.model_dump(mode="json")
        # load back and then store with indents
        return task_json
