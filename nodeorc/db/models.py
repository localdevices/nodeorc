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
        default={"url": "./tmp", "bucket_name": "examplevideo"}
    )
    callback_url = Column(
        JSON, nullable=True,
    )
    incoming_path = Column(String, nullable=False)
    failed_path = Column(String, nullable=False)
    success_path = Column(String, nullable=False)
    results_path = Column(String, nullable=False)
    parse_dates_from_file = Column(Boolean, default=True, nullable=False)
    video_file_fmt = Column(String, nullable=False)
    water_level_fmt = Column(String)
    water_level_datetimefmt = Column(String)
    allowed_dt = Column(Float, default=3600, nullable=False)
    shutdown_after_task = Column(Boolean, default=False, nullable=False)
    disk_management = Column(
        JSON,
        nullable=False,
        default={
            "home_folder": "/home",
            "min_free_space": 20,
            "critical_space": 10,
            "frequency": 3600
        }
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
