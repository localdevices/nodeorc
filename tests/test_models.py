"""Unit tests for database models."""
import datetime
import json
import pytest
import nodeorc.models as orcmodels

from nodeorc.db import WaterLevelSettings, WaterLevelTimeSeries, Base, Callback
from nodeorc.db_ops import add_replace_water_level_script, add_water_level

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    s = Session()
    Base.metadata.create_all(engine)
    yield s
    s.close()


@pytest.fixture
def callback_instance():
    """Fixture to create a sample Callback instance."""
    return Callback(
        id=1,
        body=json.dumps({"key": "value"}),
        created_at="2023-10-18T14:00:00"
    )

@pytest.fixture
def script():
    """Fixture to create a sample script that generates a datetime and value for a water level."""
    return "echo \"2023-01-01T00:00:00Z, 1.23\""

@pytest.fixture
def python_script():
    """Fixture to create a sample python script (instead of bash) for water level retrieval."""
    return "print(\"2023-01-01T00:00:00Z, 1.23\")"



@pytest.fixture
def new_script():
    """Fixture to create a replacement sample script for water level retrieval."""
    return "echo \"2024-01-01T00:00:00Z, 1.23\""


# test configs
def test_add_new_water_level_record(session, script):
    file_template = "file_{datetime}.txt"
    frequency = 10.5
    datetime_fmt = "%Y-%m-%dT%H:%M:%SZ"

    water_level = add_replace_water_level_script(
        session=session,
        script=script,
        file_template=file_template,
        frequency=frequency,
        datetime_fmt=datetime_fmt,
    )

    assert water_level is not None
    assert water_level.script == script
    assert water_level.file_template == file_template
    assert water_level.frequency == frequency
    assert water_level.datetime_fmt == datetime_fmt

def test_add_new_water_level_record_python(session, python_script):
    file_template = "file_{datetime}.txt"
    script_type = 'python'
    frequency = 10.5
    datetime_fmt = "%Y-%m-%dT%H:%M:%SZ"

    water_level = add_replace_water_level_script(
        session=session,
        script=python_script,
        script_type=script_type,
        file_template=file_template,
        frequency=frequency,
        datetime_fmt=datetime_fmt,
    )

    assert water_level is not None
    assert water_level.script == python_script
    assert water_level.file_template == file_template
    assert water_level.frequency == frequency
    assert water_level.datetime_fmt == datetime_fmt



def test_update_existing_water_level_record(session, script, new_script):
    file_template = "file_{datetime}.txt"
    frequency = 10.5
    datetime_fmt = "%Y-%m-%dT%H:%M:%SZ"

    # Add initial record
    water_level = WaterLevelSettings(
        script=script,
        file_template=file_template,
        frequency=frequency,
        datetime_fmt=datetime_fmt,
    )
    session.add(water_level)
    session.commit()

    # Update record
    new_file_template = "updated_file_{datetime}.txt"
    new_frequency = 20.0
    new_datetime_fmt = "%d-%m-%YT%H:%M:%S"

    updated_water_level = add_replace_water_level_script(
        session=session,
        script=new_script,
        file_template=new_file_template,
        frequency=new_frequency,
        datetime_fmt=new_datetime_fmt,
    )

    assert updated_water_level is not None
    assert updated_water_level.script == new_script
    assert updated_water_level.file_template == new_file_template
    assert updated_water_level.frequency == new_frequency
    assert updated_water_level.datetime_fmt == new_datetime_fmt


def test_rollback_on_error(session, script):
    file_template = "file_{datetime}.txt"
    frequency = 10.5
    datetime_fmt = "%Y-%m-%dT%H:%M:%SZ"

    # Simulate a failure by passing an invalid parameter
    with pytest.raises(Exception):
        add_replace_water_level_script(
            session, 20 # , file_template, frequency, datetime_fmt
        )

    # Ensure no records were added
    result = session.query(WaterLevelSettings).all()
    assert len(result) == 0


def test_water_level_datetime_format_valid():
    water_level = WaterLevelSettings(datetime_fmt="%Y-%m-%dT%H:%M:%SZ")
    assert water_level.datetime_fmt == "%Y-%m-%dT%H:%M:%SZ"


def test_water_level_datetime_format_invalid():
    with pytest.raises(ValueError, match="Invalid datetime format string: .*"):
        WaterLevelSettings(datetime_fmt="invalid_format")


def test_water_level_file_template_valid():
    water_level = WaterLevelSettings(file_template="wl_{%d%m%Y}.txt")
    assert water_level.file_template == "wl_{%d%m%Y}.txt"


def test_water_level_file_template_invalid_no_braces():
    water_level = WaterLevelSettings(file_template="valid_single_file.txt")
    assert water_level.file_template == "valid_single_file.txt"


def test_water_level_file_template_invalid_format():
    with pytest.raises(ValueError, match="Invalid datetime format in .*"):
        WaterLevelSettings(file_template="wl_{%Q}.txt")


def test_water_level_retrieval_frequency_valid():
    water_level = WaterLevelSettings(frequency=300)
    assert water_level.frequency == 300


def test_water_level_retrieval_frequency_negative():
    with pytest.raises(ValueError, match="frequency must be a positive value."):
        WaterLevelSettings(frequency=-1)


def test_water_level_retrieval_frequency_too_high():
    with pytest.raises(ValueError, match="frequency must be less than 86400 .*"):
        WaterLevelSettings(frequency=90000)


def test_water_level_script_valid(mocker):
    mocker.patch("nodeorc.water_level.execute_water_level_script", return_value="2023-01-01T00:00:00Z, 1.23")
    water_level = WaterLevelSettings(script="valid_script.py")
    assert water_level.script == "valid_script.py"


def test_water_level_script_invalid(session, mocker):
    mocker.patch("nodeorc.water_level.execute_water_level_script", side_effect=Exception("Script execution failed"))
    with pytest.raises(ValueError, match="Error while validating script: *"):
        instance = WaterLevelSettings(script="invalid_script.py")
        session.add(instance)
        session.commit()



def test_water_level_ts_creation(session):
    timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
    level = 5.0
    water_level = WaterLevelTimeSeries(timestamp=timestamp, level=level)

    session.add(water_level)
    session.commit()

    retrieved = session.query(WaterLevelTimeSeries).first()
    assert retrieved is not None
    assert retrieved.timestamp == timestamp
    assert retrieved.level == level


def test_water_level_ts_default_timestamp(session):
    level = 4.2
    water_level = WaterLevelTimeSeries(level=level)

    session.add(water_level)
    session.commit()

    retrieved = session.query(WaterLevelTimeSeries).first()
    assert retrieved is not None
    assert isinstance(retrieved.timestamp, datetime.datetime)
    assert retrieved.level == level


def test_water_level_ts_no_level(session):
    with pytest.raises(IntegrityError):
        wl = WaterLevelTimeSeries()
        session.add(wl)
        session.commit()


def test_add_water_level_already_exists(session):
    timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
    level = 5.0
    water_level = WaterLevelTimeSeries(timestamp=timestamp, level=level)
    session.add(water_level)
    session.commit()
    # now test function
    water_level_existing = add_water_level(session, timestamp, level)
    # check total amount of time stamps
    water_levels = session.query(WaterLevelTimeSeries).all()
    assert len(water_levels) == 1
    assert water_level_existing.id == water_level.id


def test_add_water_level_new(session):
    timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
    level = 5.0
    water_level = add_water_level(session, timestamp, level)
    # now add a new timestamp and level
    new_timestamp = datetime.datetime(2023, 1, 1, 12, 1, 0)
    new_level = 6.0
    new_water_level = add_water_level(session, new_timestamp, new_level)
    # check total amount of time stamps
    water_levels = session.query(WaterLevelTimeSeries).all()
    assert len(water_levels) == 2
    # check difference
    assert new_water_level.id != water_level.id


def test_callback_str_method(callback_instance):
    """Test the __str__ method of the Callback class."""
    result = str(callback_instance)
    assert result == '{"key": "value"}'


def test_callback_repr_method(callback_instance):
    """Test the __repr__ method of the Callback class."""
    result = repr(callback_instance)
    assert result == '{"key": "value"}'


def test_callback_property(callback_instance):
    """Test the callback property method."""
    result = callback_instance.callback
    assert isinstance(result, orcmodels.Callback)
    assert result.func_name == "discharge"
