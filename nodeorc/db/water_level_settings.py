"""Model for water level settings."""
import enum
import re

from datetime import datetime
from sqlalchemy import event, Boolean, Column, String, DateTime, Integer, Float, Enum
from sqlalchemy.orm import validates

from nodeorc import water_level
from nodeorc.db import Base

class ScriptType(enum.Enum):
    PYTHON = 0
    BASH = 1

class WaterLevelSettings(Base):
    __tablename__ = "water_level"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    datetime_fmt = Column(
        String,
        default="%Y-%m-%dT%H:%M:%SZ",
        comment="Datestring format of water level file, e.g. %Y-%m-%dT%H:%M:%SZ"
    )
    file_template = Column(
        String,
        default="wl_{%Y%m%d}.txt",
        comment="Filename template (excluding path) defining the file name convention of files containing water "
                "levels. Files are only used as fallback if there is no entry in the database. "
                "e.g. wl_{%Y%m%d}.txt. Water level files are expected in <nodeorc home folder>/water_level/"
    )
    frequency = Column(
        Float,
        default=600,
        comment="Frequency [s] in which a device or API will be checked for available water level files and "
                "water level entries will be added to the database, using the scripts. "
    )
    script_type = Column(
        Enum(ScriptType),
        default=ScriptType.PYTHON,
        comment="Type of script used to retrieve water level data from the device or API. Either 'PYTHON' or 'BASH'."
    )
    script = Column(
        String,
        default="print(\"2000-01-01T00:00:00Z, 10\")",
        comment="Content of the script to be executed to retrieve water level data from the device or API. Script must "
                "print a water level value to stdout in the form \"%Y-%m-%dT%H:%M:%SZ, <value>\""
    )
    optical = Column(
        Boolean,
        default=True,
        comment="Whether to measure water level optically if no water level can be retrieved from the database or "
                "files. "
    )
    def __str__(self):
        return "WaterLevel: {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

    @validates('datetime_fmt')
    def validate_datetime_format(self, key, value):
        """Validate that the provided string is a valid datetime format string."""
        if not "%" in value:
            raise ValueError("Invalid datetime format string: % is missing.")
        try:
            # Test the format using strptime with a sample date
            _ = datetime.strptime(
                datetime.now().strftime(value),
                value
            )
        except ValueError:
            raise ValueError(f"Invalid datetime format string: {value}")
        return value

    @validates("file_template")
    def validate_file_template(self, key, value):
        """Validate that the template contains a valid datetime format string within curly braces ({...})."""
        # Search for a pattern inside curly braces
        datetime_format_match = re.search(r"\{([^}]+)\}", value)
        if not datetime_format_match:
            # apparently one single file is used, so we are done validating, return value
            return value
        datetime_format = datetime_format_match.group(1)
        try:
            # Validate the datetime format by string formatting it, and then parsing it back to a datetime instance
            _ = datetime.strptime(
                datetime.now().strftime(datetime_format),
                datetime_format
            )
        except ValueError:
            raise ValueError(f"Invalid datetime format in '{{{datetime_format}}}'.")
        return value

    @validates('frequency')
    def validate_frequency(self, key, value):
        if value is None or value <= 0:
            raise ValueError("frequency must be a positive value.")
        if value > 86400:
            raise ValueError("frequency must be less than 86400 (i.e. at least once per day).")
        return value


@event.listens_for(WaterLevelSettings, "before_insert")
@event.listens_for(WaterLevelSettings, "before_update")
def validate_script(mapper, connection, target):
    """
    Validates the script column by running the provided script using the function
    `nodeorc.water_level.execute_water_level_script` and checking its output.
    """
    if target.script is None:
        # use default script instead
        return
    if not isinstance(target.script, str):
        raise ValueError("script must be a string.")
    if target.script:
        try:
            # Execute the script and capture its output
            _ = water_level.execute_water_level_script(target.script, target.script_type)
        except Exception as e:
            raise ValueError(
                f"Error while validating script: {str(e)}"
            )
    print("Script validated successfully.")

