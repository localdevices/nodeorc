import os
import pytest

from datetime import datetime, timedelta
from pytz import UTC
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from nodeorc import models, log
from nodeorc.db import models as db_models

# Example fixture
@pytest.fixture
def session_config(tmpdir):
    db_path = ":memory:" #?cache=shared"
    # Create an in-memory SQLite database for testing; adjust connection string for other databases
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Create all tables from metadata (assumes models use SQLAlchemy Base)
    db_models.Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    try:
        # Create and add a Device instance
        device_instance = db_models.Device(
            # Add relevant fields for the Device model
            name="Test Device",

        )
        # Create and add a Settings instance
        # Add test data
        settings_instance = db_models.Settings(
            parse_dates_from_file=True,
            video_file_fmt="video_{%Y%m%dT%H%M%S}.mp4",
            allowed_dt=3600,
            shutdown_after_task=False,
            reboot_after=0,
        )
        storage_instance = db_models.Storage()
        disk_management_instance = db_models.DiskManagement(home_folder=str(tmpdir))
        water_level_settings_instance = db_models.WaterLevelSettings()
        callback_url_instance = db_models.CallbackUrl(server_name="testserver")
        session.add(device_instance)
        session.add(settings_instance)
        session.add(storage_instance)
        session.add(disk_management_instance)
        session.add(water_level_settings_instance)
        session.add(callback_url_instance)
        # commit to give all an id
        session.commit()

        active_config_instance = db_models.ActiveConfig(
            settings_id=settings_instance.id,
            storage_id=storage_instance.id,
            disk_management_id=disk_management_instance.id,
            callback_url_id=callback_url_instance.id,

        )
        session.add(active_config_instance)
        # Commit the session to save changes
        session.commit()

        yield session  # Provide the session to tests

    finally:
        # Close the session and drop all tables after tests run
        session.close()
        db_models.Base.metadata.drop_all(engine)


@pytest.fixture
def session_water_levels(session_config):
    from datetime import timezone
    # create a bunch of water level in the database around the current datetime
    timestamps = [datetime.now() + timedelta(hours=h) for h in range(-4, 5)]
    values = list(range(len(timestamps)))
    # make several timestamps to store
    for t, v in zip(timestamps, values):
        water_level_instance = db_models.WaterLevelTimeSeries(
            timestamp=t,
            level=v,
        )
        session_config.add(water_level_instance)
    session_config.commit()
    return session_config


@pytest.fixture
def video_sample_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere_20191103.mp4"

@pytest.fixture
def recipe_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere.yml"


@pytest.fixture
def camconfig_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere.json"


@pytest.fixture
def crossection_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/cross_section1.geojson"

@pytest.fixture
def output_nc():
    return os.path.join(os.path.dirname(__file__), "examples", "ngwerere_transect.nc")


@pytest.fixture
def logger():
    return log.start_logger(True, False)


@pytest.fixture
def callback_url():
    obj = models.CallbackUrl(
        url="http://127.0.0.1:1080",
        token=None,
        refresh_token=None,
    )
    return obj

@pytest.fixture
def callback_url_amqp():
    obj = models.CallbackUrl(
        url="http://mockserver:1080",
        token=None
    )
    return obj



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

