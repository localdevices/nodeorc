"""Base model for all models."""
import json

from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta

# database set up
Base = declarative_base()


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