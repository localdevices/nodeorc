from pydantic import field_validator, BaseModel, AnyHttpUrl, DirectoryPath, StrictBool

# nodeodm specific imports
from . import check_datetime_fmt
class LocalConfig(BaseModel):
    incoming_path: DirectoryPath
    failed_path: DirectoryPath
    success_path: DirectoryPath
    results_path: DirectoryPath
    parse_dates_from_file: StrictBool = False
    video_file_fmt: str
    water_level_fmt: str
    water_level_datetimefmt: str

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

