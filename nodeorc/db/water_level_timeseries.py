"""Model for water level time series."""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Float
from nodeorc.db import Base

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
