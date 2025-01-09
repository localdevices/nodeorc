"""Model for callback."""
import json

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, JSON

from nodeorc import models
from nodeorc.db.models import Base


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


