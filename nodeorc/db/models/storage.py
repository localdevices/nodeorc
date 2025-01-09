"""Model for storage."""

import os
import shutil

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from nodeorc.db.models import Base
import nodeorc.models as models

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

    @property
    def pydantic(self):
        """Return pydantic model of Storage record."""
        return models.Storage(url=self.url, bucket_name=self.bucket_name)

