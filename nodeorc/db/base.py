"""Base model for all models."""
import json

from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, mapped_column
from sqlalchemy.ext.declarative import DeclarativeMeta

# database set up
Base = declarative_base()


class RemoteBase(Base):
    """Base class for all models that can have remote neighbours."""
    __abstract__ = True
    __abstract__ = True
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now())
    remote_id = mapped_column(Integer, nullable=True, unique=True)
    remote_site = mapped_column(Integer, nullable=True)
    sync_status = mapped_column(Boolean, nullable=True)

    def callback(self):
        # default callback requirements
        # url = ...
        pass

# encoding to JSON
class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle SQLAlchemy model instances
        if isinstance(obj.__class__, DeclarativeMeta):
            fields = {}
            for field in obj.__table__.columns:
                value = getattr(obj, field.name)
                # Handle non-serializable values like datetime
                if isinstance(value, datetime):
                    fields[field.name] = value.isoformat()
                else:
                    fields[field.name] = value
            return fields

        # Fallback for unknown/default types
        return super().default(obj)


# encode to a dict
def sqlalchemy_to_dict(obj):
    """
    Convert a SQLAlchemy model instance into a Python dictionary.
    Handles only direct column data (no relationships to avoid recursion).
    """
    if not isinstance(obj.__class__, DeclarativeMeta):
        raise TypeError("This function only works with SQLAlchemy model instances.")

    fields = {}
    for field in obj.__table__.columns:
        value = getattr(obj, field.name)
        if isinstance(value, datetime):  # Convert datetime to ISO format
            fields[field.name] = value.isoformat()
        else:
            fields[field.name] = value
    return fields
