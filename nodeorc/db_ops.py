import sqlalchemy

from datetime import datetime
from typing import Optional, Literal

from nodeorc import db

def add_config(
        session: sqlalchemy.orm.session.Session,
        config_data: dict,
        set_as_active=True
):
    """
    Add a configuration as new record to Config table

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
    config_data : dict
    set_as_active : bool

    Returns
    -------

    """
    settings_record = db.Settings(**config_data["settings"]) if "settings" in config_data else None
    disk_management_record = db.DiskManagement(**config_data["disk_management"]) if "disk_management" in config_data else None
    storage_record = db.Storage(**config_data["storage"]) if "storage" in config_data else None
    callback_url_record = db.CallbackUrl(**config_data["callback_url"]) if "callback_url" in config_data else None
    # if "storage" in config_data:
    #     storage = config_data["storage"]
    #     storage.pop("options")  # get rid of options parameter, not relevant for dbase
    #     storage_record = db.Storage(**storage)
    # else:
    #     storage_record = None
    #
    # # callback_url_record = db_models.CallbackUrl(**config_dict["callback_url"])
    # if "callback_url" in config_data:
    #     url = config_data["callback_url"]
    #     url["url"] = str(url["url"])
    #     callback_url_record = db.CallbackUrl(**url)
    # else
    #     callback_url_record = None
    session.add(settings_record) if settings_record else None
    session.add(disk_management_record) if disk_management_record else None
    session.add(storage_record) if storage_record else None
    session.add(callback_url_record) if callback_url_record else None
    session.commit()
    if set_as_active:
        active_config_record = add_replace_active_config(
            session,
            settings_record=settings_record,
            disk_management_record=disk_management_record,
            storage_record=storage_record,
            callback_url_record=callback_url_record
        )
        return active_config_record


def add_replace_active_config(
        session,
        settings_record=None,
        disk_management_record=None,
        storage_record=None,
        callback_url_record=None
):
    """Set config as the currently active config."""
    active_configs = session.query(db.ActiveConfig)
    if len(active_configs.all()) == 0:
        # check if all records are present
        assert(
                None not in [
            settings_record,
            disk_management_record,
            storage_record,
            callback_url_record
        ]
        ), "No active configuration available yet, you need to supply settings, disk_management, storage and callback_url in your configuration. One or more are missing."
        # no active config yet, make a new one
        active_config_record = db.ActiveConfig(
            settings_id=settings_record.id,
            disk_management_id=disk_management_record.id,
            storage_id=storage_record.id,
            callback_url_id=callback_url_record.id,
        )
        session.add(active_config_record)
    else:
        # active config already exists, replace config
        active_config_record = get_active_config()
        if settings_record:
            active_config_record.settings = settings_record
            # active_config_record.settings_id = settings_record.id
        if disk_management_record:
            active_config_record.disk_management = disk_management_record
        if storage_record:
            active_config_record.storage = storage_record
        if callback_url_record:
            active_config_record.callback_url = callback_url_record
    session.commit()
    return active_config_record

from sqlalchemy.orm import Session
from nodeorc.db import WaterLevelSettings, WaterLevelTimeSeries


def add_replace_water_level_script(
    session: Session,
    script: Optional[str] = None,
    script_type: Optional[Literal["python", "bash"]] = None,
    file_template: Optional[str] = None,
    frequency: Optional[float] = None,
    datetime_fmt: Optional[str] = None
):
    """
    Creates a new WaterLevel record, or updates an existing one, using SQLAlchemy.

    Parameters
    ----------
    session : Session
        Active SQLAlchemy database session
    script : str, optional
        content of the script to save in WaterLevel
    script_type : str, optional ["python", "bash"]
        Type of script
    file_template : str, optional
        template of the file to associate with the record, possibly containing datetime placeholder in curly braces
    frequency: float, optional
        water level update frequency (seconds). New water levels will be retrieved every `frequency` seconds.
    datetime_fmt: str
        datetime format for parsing timestamps, e.g. "%Y-%m-%dT%H:%M:%SZ"
    """
    try:
        # Query for an existing WaterLevel record, if already existing, replace
        water_level = session.query(WaterLevelSettings).first()
        if water_level:
            # If the record exists, update its fields with the new information
            water_level.script = script if script else water_level.script
            water_level.script_type = script_type if script_type else water_level.script_type
            water_level.file_template = file_template if file_template else water_level.file_template
            water_level.frequency = frequency if frequency else water_level.frequency
            water_level.datetime_fmt = datetime_fmt if datetime_fmt else water_level.datetime_fmt
            session.commit()  # Commit the updated record to the database
            print(f"Updated existing WaterLevel record with ID: {water_level.id}")
        else:
            # If no record exists, create a new one
            water_level_data = {
                key: value for key, value in {
                    "script": script,
                    "script_type": script_type,
                    "file_template": file_template,
                    "frequency": frequency,
                    "datetime_fmt": datetime_fmt,
                }.items() if value is not None
            }
            water_level = WaterLevelSettings(
                **water_level_data
            )
            session.add(water_level)  # Add the new record to the session
            session.commit()  # Commit the new record to the database
            print(f"Created new WaterLevel record with ID: {water_level.id}")
        return water_level
    except Exception as e:
        # Rollback the session in case of an error to prevent breaking the database state
        session.rollback()
        raise ValueError(f"Error occurred: {e}")

def get_session():
    return db.session

def get_settings(session, id):
    """
    Get a Config pydantic object from a stored db model

    Parameters
    ----------
    config_record : db.Config
        configuration

    Returns
    -------

    """
    return session.query(db.Settings).get(id)


def get_active_config(session=db.session):
    active_configs = session.query(db.ActiveConfig)
    if len(active_configs.all()) == 0:
        return None
    active_config = active_configs.first()
    return active_config


def get_active_task_form(session, parse=False, allow_candidate=True):
    query = session.query(db.TaskForm)
    if len(query.all()) == 0:
        # there are no task forms yet, return None
        return None

    # assume a search in the accepted task forms is needed
    get_accepted = True
    if allow_candidate:
        # first check for a candidate
        query_candidate = query.filter_by(status=db.TaskFormStatus.CANDIDATE)
        if len(query_candidate.all()) > 0:
            # accepted task form not needed
            get_accepted = False
            query = query_candidate

    if get_accepted:
        # find the single task form that is active
        query = query.filter_by(status=db.TaskFormStatus.ACCEPTED)
        if len(query.all()) == 0:
            return None
    task_form = query.first()
    # check if task body can be parsed. If version upgrade occurred this may turn invalid
    if parse:
        task_form = task_form.task_body
    return task_form


def get_water_level_config(session):
    query = session.query(WaterLevelSettings)
    if len(query.all()) == 0:
        # there are no task forms yet, return None
        return None
    return session.query(WaterLevelSettings).first()


def patch_active_config_to_accepted():
    """If active config is still CANDIDATE, upgrade to ACCEPTED """
    task_form_row = get_active_task_form(db.session)
    if task_form_row.status == db.TaskFormStatus.CANDIDATE:
        # also retrieve the accepted
        task_form_row_accepted = get_active_task_form(
            db.session,
            allow_candidate=False
        )
        # now change the statusses
        if task_form_row_accepted:  # it may also be that there are no ACCEPTED forms yet
            task_form_row_accepted.status = db.TaskFormStatus.ANCIENT
        task_form_row.status = db.TaskFormStatus.ACCEPTED
        db.session.commit()


def get_data_folder():
    config = get_active_config()
    if config:
        return config.disk_management.home_folder
    return None


def add_water_level(
    session: Session,
    timestamp: datetime,
    level: float
):
    """
    Adds a new water level record to the database using the provided session.

    Parameters
    ----------
    session : Session
        Active SQLAlchemy database session.
    timestamp : datetime
        Timestamp of the water level reading.
    level : float
        Water level value [m].

    Returns
    -------
    WaterLevelTimeSeries
        The created water level record.
    """
    try:
        # check if the time stamp already exists in the database
        water_level = session.query(WaterLevelTimeSeries).filter_by(timestamp=timestamp).first()
        if not water_level:
            # Create a new instance of WaterLevelSettings with given data
            water_level = WaterLevelTimeSeries(
                timestamp=timestamp,
                level=level
            )
            session.add(water_level)  # Add record to the session
            session.commit()  # Commit the transaction
        return water_level  # Return the new record
    except Exception as e:
        # Rollback session in case of an error
        session.rollback()
        raise ValueError(f"Failed to add water level: {e}")


def get_water_level(
    session: Session,
    timestamp: datetime,
    allowed_dt: Optional[float] = None,
):
    """Fetch the water level closest to the given timestamp.

    This function queries a database to find the water level record that is closest
    to the specified timestamp. If both prior and subsequent water level records
    exist, it determines the closest one based on the absolute time difference.
    Optionally, it checks whether the closest record falls within an allowed
    time difference from the specified timestamp.

    Parameters
    ----------
    session : Session
        Database session used to query water level records.
    timestamp : datetime
        The point in time for which the closest water level record is sought.
    allowed_dt : float, optional
        Maximum allowed time difference, in seconds, between the closest
        record's timestamp and the specified timestamp. If provided,
        the function raises a ValueError if no record fits within this range.

    Returns
    -------
    WaterLevelTimeSeries
        The water level record closest to the specified timestamp.

    Raises
    ------
    ValueError
        If no water level record is found or if no record is within the allowed
        time difference from the specified timestamp when `allowed_dt` is used.
    """
    # SQLite does not allow for tzinfo in a time stamp, therefore, first remove the tzinfo if it exists
    timestamp = timestamp.replace(tzinfo=None)
    before_record = session.query(WaterLevelTimeSeries).filter(WaterLevelTimeSeries.timestamp <= timestamp).order_by(WaterLevelTimeSeries.timestamp.desc()).first()
    after_record = session.query(WaterLevelTimeSeries).filter(WaterLevelTimeSeries.timestamp > timestamp).order_by(WaterLevelTimeSeries.timestamp).first()
    
    # Determine the closest record
    closest_record = None
    if before_record and after_record:
        if abs((before_record.timestamp - timestamp).total_seconds()) <= abs((after_record.timestamp - timestamp).total_seconds()):
            closest_record = before_record
        else:
            closest_record = after_record
    elif before_record:
        closest_record = before_record
    elif after_record:
        closest_record = after_record

    if not closest_record:
        raise ValueError(f"No water level entries found for timestamp: {timestamp}")

    if allowed_dt:
        # Ensure the time difference is within the allowed range
        diff = abs((closest_record.timestamp - timestamp).total_seconds())
        if diff > allowed_dt:
            raise ValueError(f"No water level found within {allowed_dt} seconds of timestamp {timestamp}.")

    return closest_record
