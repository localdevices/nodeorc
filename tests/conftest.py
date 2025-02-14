import os
import pytest

from datetime import datetime, timedelta
from pytz import UTC
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from nodeorc import models, log
from nodeorc import db


@pytest.fixture
def session_empty(tmpdir):
    db_path = ":memory:" #?cache=shared"
    # Create an in-memory SQLite database for testing; adjust connection string for other databases
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Create all tables from metadata (assumes models use SQLAlchemy Base)
    db.Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    yield session
    # Close the session and drop all tables after tests run
    session.close()
    db.Base.metadata.drop_all(engine)


# Example fixture
@pytest.fixture
def session_config(session_empty, tmpdir):
    session = session_empty
    # Create and add a Device instance
    device_instance = db.Device(
        # Add relevant fields for the Device model
        name="Test Device",

    )
    # Create and add a Settings instance
    # Add test data
    settings_instance = db.Settings(
        parse_dates_from_file=True,
        video_file_fmt="video_{%Y%m%dT%H%M%S}.mp4",
        allowed_dt=3600,
        shutdown_after_task=False,
        reboot_after=0,
    )
    disk_management_instance = db.DiskManagement(home_folder=str(tmpdir))
    water_level_settings_instance = db.WaterLevelSettings()
    callback_url_instance = db.CallbackUrl()
    session.add(device_instance)
    session.add(settings_instance)
    session.add(disk_management_instance)
    session.add(water_level_settings_instance)
    session.add(callback_url_instance)
    # commit to give all an id
    session.commit()
    return session  # Provide the session to tests



@pytest.fixture
def session_water_levels(session_config):
    from datetime import timezone
    # create a bunch of water level in the database around the current datetime
    timestamps = [datetime.now() + timedelta(hours=h) for h in range(-4, 5)]
    values = list(range(len(timestamps)))
    # make several timestamps to store
    for t, v in zip(timestamps, values):
        water_level_instance = db.TimeSeries(
            timestamp=t,
            h=v,
        )
        session_config.add(water_level_instance)
    session_config.commit()
    return session_config


@pytest.fixture
def logger():
    return log.start_logger(True, False)


@pytest.fixture
def callback(output_nc):
    obj = models.Callback(
        file=models.File(
            tmp_name=os.path.split(output_nc)[1],
            remote_name=os.path.split(output_nc)[1]
        ),
        func_name="discharge",
        kwargs={},
        storage=models.Storage(
            url="",
            bucket_name=os.path.split(output_nc)[0]
        ),
        endpoint="/api/timeseries/"  # used to extend the default callback url
    )
    return obj


@pytest.fixture
def callback_patch():
    obj = models.Callback(
        func_name="discharge",
        kwargs={},
        request_type="PATCH",
        endpoint="/api/timeseries/1"  # used to extend the default callback url
    )
    return obj

