import os
from pydantic import field_validator, BaseModel, AnyHttpUrl, DirectoryPath, StrictBool, ValidationError
from pathlib import PosixPath
from typing import Optional
# nodeodm specific imports
from . import check_datetime_fmt
from . import Storage, CallbackUrl
import click

class DiskManagement(BaseModel):
    # default parameters for disk management, these will in most cases on linux systems be appropriate
    home_folder: str = "/home"
    min_free_space: float = 20.0  # if space is less than this threshold, files will be (re)moved.
    critical_space: float = 10.0  # if space is less than this threshold, the service will shutdown immediately to
    # prevent access problems
    frequency: int = 86400  # frequency to check the values in seconds

    @field_validator("home_folder")
    @classmethod
    def check_homefolder(cls, v):
        # check string within {}, see if that can be parsed to datetime
        if not(os.path.isdir(v)):
            raise IOError(f"home_folder {v} is not available, disk may be disconnected or wrong path supplied.")
        return v

    @property
    def incoming_path(self):
        p = os.path.join(self.home_folder, "incoming")
        if not(os.path.isdir(p)):
            try:
                os.makedirs(p)
            except:
                # directory creation fails, e.g. because of rights or unavailability of disk (USB stick removed).
                return None
        return p

    @property
    def failed_path(self):
        p = os.path.join(self.home_folder, "failed")
        if not(os.path.isdir(p)):
            os.makedirs(p)
        return p

    @property
    def success_path(self):
        p = os.path.join(self.home_folder, "success")
        if not(os.path.isdir(p)):
            os.makedirs(p)
        return p

    @property
    def results_path(self):
        p = os.path.join(self.home_folder, "results")
        if not(os.path.isdir(p)):
            os.makedirs(p)
        return p

    @property
    def water_level_path(self):
        p = os.path.join(self.home_folder, "water_level")
        if not(os.path.isdir(p)):
            os.makedirs(p)
        return p

    @property
    def log_path(self):
        p = os.path.join(self.home_folder, "log")
        if not(os.path.isdir(p)):
            os.makedirs(p)
        return p

    @property
    def tmp_path(self):
        p = os.path.join(self.home_folder, "tmp")
        if not(os.path.isdir(p)):
            os.makedirs(p)
        return p

class Settings(BaseModel):
    # incoming_path: DirectoryPath
    # failed_path: DirectoryPath
    # success_path: DirectoryPath
    # results_path: DirectoryPath
    parse_dates_from_file: StrictBool = False
    video_file_fmt: str
    water_level_fmt: str
    water_level_datetimefmt: str
    allowed_dt: float
    shutdown_after_task: StrictBool = False
    reboot_after: float = 0

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


class RemoteConfig(BaseModel):
    amqp_connection: AnyHttpUrl


class LocalConfig(BaseModel):
    settings: Settings
    storage: Storage
    callback_url: Optional[CallbackUrl]
    disk_management: DiskManagement = DiskManagement()

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

