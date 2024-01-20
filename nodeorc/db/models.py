from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, JSON, Boolean, Float
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import datetime

Base = declarative_base()

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    storage = Column(
        JSON, nullable=False,
        default={"url": "./tmp", "bucket_name": "examplevideo"},
        doc="storage details",
        comment='JSON describing the storage as {"url": "<url>", "storage_bucket": "/path/to/bucket"}'
    )
    incoming_path = Column(
        String,
        nullable=False,
        comment="Path to incoming videos"
    )
    failed_path = Column(
        String,
        nullable=False,
        comment="Path to failed videos"
    )
    success_path = Column(
        String,
        nullable=False,
        comment = "Path to successfully treated videos"
    )
    results_path = Column(
        String,
        nullable=False,
        comment = "Path to results"
    )
    parse_dates_from_file = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag determining if dates should be read from file metadata (True, default) or from a datestring in the filename (False)"
    )
    video_file_fmt = Column(
        String,
        nullable=False,
        comment="Filename template (excluding path) defining the file name convention of video files. The template contains a datestring format in between {} signs, e.g. video_{%Y%m%dT%H%M%S}.mp4"
    )
    water_level_fmt = Column(
        String,
        comment="Filename template (including path) defining the file name convention of files containing water levels. The template contains a datestring format in between {} signs, e.g. /home/orc/water_level/wl_{%Y%m%d}.txt"
    )
    water_level_datetimefmt = Column(
        String,
        comment="Datestring format of water level file, e.g. %Y-%m-%dT%H:%M:%S"

    )
    allowed_dt = Column(
        Float,
        default=3600,
        nullable=False,
        comment="Float indicating the maximum difference in time allowed between a videofile time stamp and a water level time stamp to match them"
    )
    shutdown_after_task = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag for enabling automated shutdown after a task is performed. Must only be used if a power cycling scheme is implemented and is meant to save power only."
    )
    disk_management = Column(
        JSON,
        nullable=False,
        default={
            "home_folder": "/home",
            "min_free_space": 20,
            "critical_space": 10,
            "frequency": 3600
        },
        comment='JSON providing information on how to cleanup the disks if space is getting critical containing {"home_folder": "/path/to/folder/to/check/for/available/space", "min_free_space": <amount-of-GB>, "critical_space": <amount-of-GB>, "frequency": <frequency-in-seconds>}'
    )

    def __str__(self):
        return "Settings {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())


class DiskManagement(Base):
    __tablename__ = 'disk_management'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
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


class ActiveConfig(Base):
    __tablename__ = "active_config"
    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey("settings.id"), nullable=False)
    callback_url_id = Column(Integer, ForeignKey("callback_url.id"), nullable=False)
    disk_management_id = Column(Integer, ForeignKey("disk_management.id"), nullable=False)
    storage_id = Column(Integer, ForeignKey("storage.id"), nullable=False)
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