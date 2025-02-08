"""Model for water level time series."""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, JSON
from nodeorc.db import RemoteBase

class Profile(RemoteBase):
    """
    Represents a profile entity in a database.

    This class maps to the "profile" table within a database and is used to store
    information about a profile (cross-section). It includes attributes for profile identification,
    timestamp, name, and associated data, all of which are represented as columns
    in the table.

    Attributes
    ----------
    id : int
        The primary key unique identifier for the profile.
    timestamp : datetime
        The timestamp indicating when the profile was created or recorded. Defaults
        to the current datetime if not provided.
    name : str
        The name of the profile.
    data : dict
        A JSON representation of additional data or metadata associated with
        the profile.
    """
    __tablename__ = "profile"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now())
    name = Column(String)
    data = Column(JSON)
    def __str__(self):
        return "{}: {}".format(self.timestamp, self.level)

    def __repr__(self):
        return "{}".format(self.__str__())
