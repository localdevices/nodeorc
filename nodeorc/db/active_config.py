"""Model for entire configuration of device."""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from nodeorc.db import Base


class ActiveConfig(Base):
    __tablename__ = "active_config"
    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey("settings.id"), nullable=False, comment="general settings of local paths, formats and device behaviour.")
    callback_url_id = Column(Integer, ForeignKey("callback_url.id"), nullable=False, comment="url, and login tokens for reporting to web service.")
    disk_management_id = Column(Integer, ForeignKey("disk_management.id"), nullable=False, comment="settings for managing disk space in case low disk space occurs.")
    storage_id = Column(Integer, ForeignKey("storage.id"), nullable=False, comment="local or remote storage settings.")
    settings = relationship(
        "Settings",
        foreign_keys=[settings_id]
    )
    disk_management = relationship(
        "DiskManagement",
        foreign_keys=[disk_management_id]
    )
    callback_url = relationship(
        "CallbackUrl",
        foreign_keys=[callback_url_id]
    )
    storage = relationship(
        "Storage",
        foreign_keys=[storage_id]
    )
    def __str__(self):
        return "ActiveConfig: {} - {} - {} - {}".format(self.settings, self.disk_management, self.callback_url, self.storage)

    def __repr__(self):
        return "{}".format(self.__str__())

