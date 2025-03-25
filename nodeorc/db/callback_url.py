"""Model for callback url."""

import json

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from nodeorc.db import Base, sqlalchemy_to_dict
from nodeorc import models

class CallbackUrl(Base):
    __tablename__ = 'callback_url'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    url = Column(
        String,
        default="https://127.0.0.1:8000/api",
        nullable=False,
        comment="url to api main end point of server to report to"
    )
    token_refresh_end_point = Column(
        String,
        comment="Refresh end point for JWT tokens of the server",
        default="/api/token/refresh/"
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

    @property
    def pydantic(self):
        rec = sqlalchemy_to_dict(self)
        return models.CallbackUrl(**rec)

