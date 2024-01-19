from pydantic import field_validator, BaseModel, AnyHttpUrl, DirectoryPath, StrictBool
from pathlib import PosixPath
from typing import Optional
# nodeodm specific imports
from . import check_datetime_fmt
from . import Storage, CallbackUrl

class DiskManagement(BaseModel):
    # default parameters for disk management, these will in most cases on linux systems be appropriate
    home_folder: DirectoryPath = PosixPath("/home")
    min_free_space: float = 20.0  # if space is less than this threshold, files will be (re)moved.
    critical_space: float = 10.0  # if space is less than this threshold, the service will shutdown immediately to
    # prevent access problems
    frequency: int = 86400  # frequency to check the values in seconds


class LocalConfig(BaseModel):
    storage: Storage
    callback_url: Optional[CallbackUrl]
    incoming_path: DirectoryPath
    failed_path: DirectoryPath
    success_path: DirectoryPath
    results_path: DirectoryPath
    parse_dates_from_file: StrictBool = False
    video_file_fmt: str
    water_level_fmt: str
    water_level_datetimefmt: str
    allowed_dt: float
    shutdown_after_task: StrictBool = False
    disk_management: DiskManagement = DiskManagement()

    @field_validator("video_file_fmt")
    @classmethod
    def check_video_fmt(cls, v):
        # check string within {}, see if that can be parsed to datetime
        check_datetime_fmt(v)
        return v


    @field_validator("water_level_fmt")
    @classmethod
    def check_water_level_fmt(cls, v):
        check_datetime_fmt(v)
        return v

    def to_file(self, fn, indent=4, **kwargs):
        with open(fn, "w") as f:
            f.write(self.to_json(indent=4, **kwargs))

    def to_json(self, indent=0):
        """
        Write task to fully serializable json format

        Parameters
        ----------
        indent : int
            indentation of json string (typically only used for

        Returns
        -------

        """
        return self.model_dump_json(indent=indent)
        # load back and then store with indents
        return task_json


class RemoteConfig(BaseModel):
    amqp_connection: AnyHttpUrl

