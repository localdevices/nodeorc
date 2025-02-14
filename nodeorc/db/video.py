"""Model for water level time series."""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Enum
from sqlalchemy.orm import relationship, mapped_column, Mapped
from nodeorc.db import RemoteBase
from typing import Optional

class VideoStatus(enum.Enum):
    NEW = 1
    QUEUE = 2
    TASK = 3
    DONE = 4
    ERROR = 5


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
    file : str or None
        The file associated with the video. Can be null.
    image : str or None
        The image associated with the video. Can be null.
    thumbnail : str or None
        The thumbnail of the video. Can be null.
    camera_config : int
        Foreign key linking to the associated camera configuration.
    """
    __tablename__ = "video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())
    status: Mapped[enum.Enum] = mapped_column(Enum(VideoStatus), default=VideoStatus.NEW)
    file: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    thumbnail: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    camera_config_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("camera_config.id"), nullable=True)  # relate by id
    # time_series = Column(ForeignKey("time_series.id"))
    camera_config = relationship("CameraConfig")
    time_series = relationship("TimeSeries", uselist=False, back_populates="video")

    def __str__(self):
        return "{}: {}".format(self.timestamp, self.file)

    def __repr__(self):
        return "{}".format(self.__str__())
