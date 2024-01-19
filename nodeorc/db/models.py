from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, JSON, Boolean, Float
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import datetime

Base = declarative_base()

class Config(Base):
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    storage = Column(
        JSON, nullable=False,
        default={"url": "./tmp", "bucket_name": "examplevideo"},
        doc="storage details",
        comment='JSON describing the storage as {"url": "<url>", "storage_bucket": "/path/to/bucket"}'
    )
    callback_url = Column(
        JSON, nullable=True,
        comment='JSON describing the callback url with token as {"server_name": "<name>", "url": <url>, "token_refresh_end_point": "/token/refresh/api/endpoint", "token_access": "<jwt-access-token>", "token_refresh": "<jwt-refresh-token>"}'
    )
    # server_name: str = "some_server"  # required only for storing access tokens
    # url: AnyHttpUrl = "https://127.0.0.1:8000/api"
    # token_refresh_end_point: Optional[str] = None
    # token_refresh: Optional[str] = None
    # token_access: Optional[str] = None
    # token_expiration: Optional[datetime] = datetime.now()

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
        return "Config {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

class ActiveConfig(Base):
    __tablename__ = "active_config"
    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey("config.id"), nullable=False)
    config = relationship(
        "Config",
        foreign_keys=[config_id]
    )

    def __str__(self):
        return "ActiveConfig: {}".format(self.config)

    def __repr__(self):
        return "{}".format(self.__str__())
