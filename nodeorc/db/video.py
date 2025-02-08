"""Model for water level time series."""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy_file import FileField, ImageField
from nodeorc.db import RemoteBase

class Video(RemoteBase):
    """
    Represents a video entity in the database.

    This class corresponds to the 'video' table in the database and provides
    fields to store metadata about a video, including timestamps, file details,
    thumbnail, and associated camera configuration. It is used to encapsulate
    the properties and attributes of video records.

    Attributes
    ----------
    __tablename__ : str
        Name of the database table ('video').
    id : int
        Primary key of the video record.
    timestamp : datetime
        The timestamp indicating when the video record was created.
    file : FileField or None
        The file associated with the video. Can be null.
    image : ImageField or None
        The image associated with the video. Can be null.
    thumbnail : ImageField or None
        The thumbnail of the video. Can be null.
    camera_config : int
        Foreign key linking to the associated camera configuration.
    """
    __tablename__ = "video"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now())
    file = Column(FileField, nullable=True)
    image = Column(ImageField, nullable=True)
    thumbnail = Column(ImageField, nullable=True)
    camera_config = Column(ForeignKey("camera_config.id"))
    def __str__(self):
        return "{}: {}".format(self.timestamp, self.level)

    def __repr__(self):
        return "{}".format(self.__str__())
