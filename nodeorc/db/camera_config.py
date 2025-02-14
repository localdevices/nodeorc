import socket
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import mapped_column, validates, relationship

from nodeorc.db import Base
import pyorc

class CameraConfig(Base):
    __tablename__ = "camera_config"
    id = Column(
        Integer,
        primary_key=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        nullable=False
    )
    name = Column(
        String,
        nullable=False,
        default=socket.gethostname()
    )
    profile_id = Column(
        Integer,
        ForeignKey("profile.id"),
        nullable=True,
    )
    camera_config = Column(
        JSON,
        nullable=False,
    )
    profile = relationship("Profile", foreign_keys=[profile_id])

    def __str__(self):
        return "{}".format(self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

    @validates('camera_config')
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

    def callback(self):
        pass