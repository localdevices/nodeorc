import enum
import json
import psutil
import platform
import re
import socket
import uuid

from datetime import datetime
from pytz import UTC
from sqlalchemy import event, Column, Enum, Integer, String, ForeignKey, DateTime, JSON, Boolean, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column, declarative_base, validates

from nodeorc import models, water_level
from nodeorc import __version__

class TaskFormStatus(enum.Enum):
    NEW = 1  # task form that does not pass through validation
    REJECTED = 2  # task form that does not pass through validation
    ACCEPTED = 3  # currently active task form
    CANDIDATE = 4  # New form, that passed validation, but not yet trialled on a full video
    ANCIENT = 5  # surpassed and no longer available for replacement
    BROKEN = 6  # task form used to be valid but no longer, e.g. due to upgrade of version of nodeorc


class DeviceStatus(enum.Enum):
    HEALTHY = 0
    LOW_VOLTAGE = 1
    LOW_STORAGE = 2
    CRITICAL_STORAGE = 3


class DeviceFormStatus(enum.Enum):
    NOFORM = 0  # set at start of device.
    VALID_FORM = 1 # Valid form available
    INVALID_FORM = 1  # if only an invalid form is available
    BROKEN_FORM = 2  # if a valid form used to exist but now is invalid due to system/software changes


# database set up
Base = declarative_base()


class Device(Base):
    __tablename__ = "device"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4()
    )
    name = Column(
        String,
        nullable=False,
        default=socket.gethostname()
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        nullable=False
    )
    operating_system = Column(
        String,
        nullable=False,
        default=platform.platform()
    )
    processor = Column(
        String,
        nullable=False,
        default=platform.processor()
    )
    memory = Column(
        Float,
        nullable=False,
        default=psutil.virtual_memory().total / (1024**3)
        # default=os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024**3)
    )
    status = Column(Enum(DeviceStatus), default=DeviceStatus.HEALTHY)
    form_status = Column(Enum(DeviceFormStatus), default=DeviceFormStatus.NOFORM)
    nodeorc_version = Column(
        String,
        default=__version__,
        nullable=False
    )
    message = Column(String, nullable=True)  # error message if any

    def __str__(self):
        return "{}".format(self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

    @property
    def as_dict(self):
        device_info = {
            key: value for key, value in self.__dict__.items() if not key.startswith('_') and not callable(value)
        }
        # replace the datetime by a time string
        device_info["created_at"] = self.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        device_info["id"] = str(self.id)
        device_info["status"] = self.status.value
        device_info["form_status"] = self.form_status.value
        device_info["nodeorc_version"] = self.nodeorc_version
        return device_info


class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    parse_dates_from_file = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag determining if dates should be read from file metadata (True, default) or from a datestring in "
                "the filename (False)"
    )
    video_file_fmt = Column(
        String,
        nullable=False,
        comment="Filename template (excluding path) defining the file name convention of video files. The template "
                "contains a datestring format in between {} signs, e.g. video_{%Y%m%dT%H%M%S}.mp4"
    )
    # water_level_fmt = Column(
    #     String,
    #     comment="Filename template (excluding path) defining the file name convention of files containing water "
    #             "levels. The template contains a datestring format in between {} signs, "
    #             "e.g. wl_{%Y%m%d}.txt. Water level files are expected in <nodeorc home folder>/water_level/"
    # )
    # water_level_datetimefmt = Column(
    #     String,
    #     comment="Datestring format of water level file, e.g. %Y-%m-%dT%H:%M:%S"
    #
    # )
    allowed_dt = Column(
        Float,
        default=3600,
        nullable=False,
        comment="Float indicating the maximum difference in time allowed between a videofile time stamp and a water "
                "level time stamp to match them"
    )
    shutdown_after_task = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag for enabling automated shutdown after a task is performed. Must only be used if a power cycling "
                "scheme is implemented and is meant to save power only."
    )
    reboot_after = Column(
        Float,
        default=0,
        nullable=False,
        comment="Float indicating the amount of seconds after which device reboots (0 means never reboot)"
    )
    def __str__(self):
        return "Settings {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())


class DiskManagement(Base):
    __tablename__ = 'disk_management'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    home_folder = Column(
        String,
        default="/home",
        comment = "Path to folder from which to scan for available disk space"
    )

    min_free_space = Column(
        Float,
        default=20,
        comment="GB of minimum free space required. When space is less, cleanup will be performed"
    )
    critical_space = Column(
        Float,
        default=10,
        comment="GB of free space under which the service will shutdown to prevent loss of contact to the device"
    )
    frequency = Column(
        Float,
        default=3600,
        comment="Frequency [s] in which the device will be checked for available space and cleanup will occur"
    )

    def __str__(self):
        return "DiskManagement {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())


class CallbackUrl(Base):
    __tablename__ = 'callback_url'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    server_name = Column(
        String,
        comment="User defined recognizable name for server"
    )
    url = Column(
        String,
        default="https://127.0.0.1:8000/api",
        nullable=False,
        comment="url to api main end point of server to report to"
    )
    token_refresh_end_point = Column(
        String,
        comment="Refresh end point for JWT tokens of the server"
    )
    token_refresh = Column(
        String,
        comment="Refresh JWT token"
    )
    token_access = Column(
        String,
        comment="JWT token"
    )
    token_expiration = Column(
        DateTime,
        comment="Date time of moment of expiry of refresh token"
    )
    def __str__(self):
        return "CallbackUrl {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())


class Storage(Base):
    __tablename__ = "storage"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    url = Column(
        String,
        default="./tmp",
        comment="Path to temporary folder for processing"
    )
    bucket_name = Column(
        String,
        default="examplevideo",
        comment="subfolder of bucket"
    )
    def __str__(self):
        return "Storage {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

class WaterLevelSettings(Base):
    __tablename__ = "water_level"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    datetime_fmt = Column(
        String,
        default="%Y-%m-%dT%H:%M:%SZ",
        comment="Datestring format of water level file, e.g. %Y-%m-%dT%H:%M:%SZ"
    )
    file_template = Column(
        String,
        default="wl_{%Y%m%d}.txt",
        comment="Filename template (excluding path) defining the file name convention of files containing water "
                "levels. Files are only used as fallback if there is no entry in the database. "
                "e.g. wl_{%Y%m%d}.txt. Water level files are expected in <nodeorc home folder>/water_level/"
    )
    frequency = Column(
        Float,
        default=600,
        comment="Frequency [s] in which a device or API will be checked for available water level files and "
                "water level entries will be added to the database, using the scripts. "
    )
    script_type = Column(
        Enum("python", "bash"),
        default="bash",
        comment="Type of script used to retrieve water level data from the device or API. Either 'python' or 'bash'."
    )
    script = Column(
        String,
        default="echo \"2000-01-01T00:00:00Z, 10\"",
        comment="Content of the script to be executed to retrieve water level data from the device or API. Script must "
                "print a water level value to stdout in the form \"%Y-%m-%dT%H:%M:%SZ, <value>\""
    )
    def __str__(self):
        return "WaterLevel: {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

    @validates('datetime_fmt')
    def validate_datetime_format(self, key, value):
        """Validate that the provided string is a valid datetime format string."""
        if not "%" in value:
            raise ValueError("Invalid datetime format string: % is missing.")
        try:
            # Test the format using strptime with a sample date
            _ = datetime.strptime(
                datetime.now().strftime(value),
                value
            )
        except ValueError:
            raise ValueError(f"Invalid datetime format string: {value}")
        return value

    @validates("file_template")
    def validate_file_template(self, key, value):
        """Validate that the template contains a valid datetime format string within curly braces ({...})."""
        # Search for a pattern inside curly braces
        datetime_format_match = re.search(r"\{([^}]+)\}", value)
        if not datetime_format_match:
            # apparently one single file is used, so we are done validating, return value
            return value
        datetime_format = datetime_format_match.group(1)
        try:
            # Validate the datetime format by string formatting it, and then parsing it back to a datetime instance
            _ = datetime.strptime(
                datetime.now().strftime(datetime_format),
                datetime_format
            )
        except ValueError:
            raise ValueError(f"Invalid datetime format in '{{{datetime_format}}}'.")
        return value

    @validates('frequency')
    def validate_frequency(self, key, value):
        if value is None or value <= 0:
            raise ValueError("frequency must be a positive value.")
        if value > 86400:
            raise ValueError("frequency must be less than 86400 (i.e. at least once per day).")
        return value


@event.listens_for(WaterLevelSettings, "before_insert")
@event.listens_for(WaterLevelSettings, "before_update")
def validate_script(mapper, connection, target):
    """
    Validates the script column by running the provided script using the function
    `nodeorc.water_level.execute_water_level_script` and checking its output.
    """
    if target.script is None:
        # use default script instead
        return
    if not isinstance(target.script, str):
        raise ValueError("script must be a string.")
    if target.script:
        try:
            # Execute the script and capture its output
            _ = water_level.execute_water_level_script(target.script, target.script_type)
        except Exception as e:
            raise ValueError(
                f"Error while validating script: {str(e)}"
            )


class ActiveConfig(Base):
    __tablename__ = "active_config"
    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey("settings.id"), nullable=False, comment="general settings of local paths, formats and device behaviour.")
    callback_url_id = Column(Integer, ForeignKey("callback_url.id"), nullable=False, comment="url, and login tokens for reporting to web service.")
    disk_management_id = Column(Integer, ForeignKey("disk_management.id"), nullable=False, comment="settings for managing disk space in case low disk space occurs.")
    storage_id = Column(Integer, ForeignKey("storage.id"), nullable=False, comment="local or remote storage settings.")
    settings = relationship(
        "Settings",
        foreign_keys=[settings_id]
    )
    disk_management = relationship(
        "DiskManagement",
        foreign_keys=[disk_management_id]
    )
    callback_url = relationship(
        "CallbackUrl",
        foreign_keys=[callback_url_id]
    )
    storage = relationship(
        "Storage",
        foreign_keys=[storage_id]
    )
    def __str__(self):
        return "ActiveConfig: {} - {} - {} - {}".format(self.settings, self.disk_management, self.callback_url, self.storage)

    def __repr__(self):
        return "{}".format(self.__str__())


class TaskForm(Base):
    __tablename__ = "task_form"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now())
    status = Column(Enum(TaskFormStatus), default=TaskFormStatus.NEW)
    task_body = Column(JSON)
    message = Column(String, nullable=True)  # error message if any


class Callback(Base):
    __tablename__ = "callback"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    body = Column(JSON)

    def __str__(self):
        return "{}".format(self.body)

    def __repr__(self):
        return "{}".format(self.__str__())

    @property
    def callback(self):
        body = json.loads(self.body)
        return models.Callback(**body)


class WaterLevelTimeSeries(Base):
    """
    Represents water level data with timestamp and value.

    This class is used to define and manage water level records in NodeORC database.
    It is designed to store the time of measurement and the corresponding water
    level value. It can be utilized for environmental monitoring, flood prediction,
    and other relevant applications. The data is stored as structured records,
    facilitating analysis and querying.

    Attributes
    ----------
    id : int
        Unique identifier for each water level record.
    timestamp : datetime
        The date and time when the water level measurement was taken. Defaults to
        the current UTC datetime at the time of record creation.
    level : float
        The measured water level value. This attribute is mandatory.
    """
    __tablename__ = "water_level_time_series"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now())
    level = Column(Float, nullable=False)

    def __str__(self):
        return "{}: {}".format(self.timestamp, self.level)

    def __repr__(self):
        return "{}".format(self.__str__())
