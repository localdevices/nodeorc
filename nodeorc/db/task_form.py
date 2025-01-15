"""Model for task form."""

import enum
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from nodeorc.db import Base

class TaskFormStatus(enum.Enum):
    NEW = 1  # task form that does not pass through validation
    REJECTED = 2  # task form that does not pass through validation
    ACCEPTED = 3  # currently active task form
    CANDIDATE = 4  # New form, that passed validation, but not yet trialled on a full video
    ANCIENT = 5  # surpassed and no longer available for replacement
    BROKEN = 6  # task form used to be valid but no longer, e.g. due to upgrade of version of nodeorc

class TaskForm(Base):
    __tablename__ = "task_form"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now())
    status = Column(Enum(TaskFormStatus), default=TaskFormStatus.NEW)
    task_body = Column(JSON)
    message = Column(String, nullable=True)  # error message if any

