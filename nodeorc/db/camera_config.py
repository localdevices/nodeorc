import platform
import socket
import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, validates

from nodeorc.db import Base
import pyorc

class CameraConfig(Base):
    __tablename__ = "camera_config"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4()
    )
    name = Column(
        String,
        nullable=False,
        default=socket.gethostname()
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        nullable=False
    )
    config = Column(
        JSON,
        nullable=False,
        default=platform.platform()
    )

    def __str__(self):
        return "{}".format(self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

    @validates('config')
    def validate_camera_config(self, key, value):
        """Validate that the provided JSON is a valid camera configuration."""
        # try to read the config with pyorc
        try:
            _ = pyorc.CameraConfig(**value)
            return value
        except Exception as e:
            raise ValueError(
                f"Error while validating camera config: {str(e)}"
            )
