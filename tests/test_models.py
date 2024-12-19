"""Unit tests for database models."""
import datetime
import json
import pytest
from nodeorc.db.models import WaterLevel, WaterLevelTimeSeries, BaseData, Callback
import nodeorc.models as orcmodels
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


# Setup test database
@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    BaseData.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def callback_instance():
    """Fixture to create a sample Callback instance."""
    return Callback(
        id=1,
        body=json.dumps({"key": "value"}),
        created_at="2023-10-18T14:00:00"
    )


def test_water_level_datetime_format_valid():
    water_level = WaterLevel(datetimefmt="%Y-%m-%dT%H:%M:%SZ")
    assert water_level.datetimefmt == "%Y-%m-%dT%H:%M:%SZ"


def test_water_level_datetime_format_invalid():
    with pytest.raises(ValueError, match="Invalid datetime format string: .*"):
        WaterLevel(datetimefmt="invalid_format")


def test_water_level_file_template_valid():
    water_level = WaterLevel(file_template="wl_{%d%m%Y}.txt")
    assert water_level.file_template == "wl_{%d%m%Y}.txt"


def test_water_level_file_template_invalid_no_braces():
    water_level = WaterLevel(file_template="valid_single_file.txt")
    assert water_level.file_template == "valid_single_file.txt"


def test_water_level_file_template_invalid_format():
    with pytest.raises(ValueError, match="Invalid datetime format in .*"):
        WaterLevel(file_template="wl_{%Q}.txt")


def test_water_level_retrieval_frequency_valid():
    water_level = WaterLevel(retrieval_frequency=300)
    assert water_level.retrieval_frequency == 300


def test_water_level_retrieval_frequency_negative():
    with pytest.raises(ValueError, match="retrieval_frequency must be a positive value."):
        WaterLevel(retrieval_frequency=-1)


def test_water_level_retrieval_frequency_too_high():
    with pytest.raises(ValueError, match="retrieval_frequency must be less than 86400 .*"):
        WaterLevel(retrieval_frequency=90000)


def test_water_level_script_valid(mocker):
    mocker.patch("nodeorc.water_level.execute_water_level_script", return_value="2023-01-01T00:00:00Z, 1.23")
    water_level = WaterLevel(script="valid_script.py")
    assert water_level.script == "valid_script.py"


def test_water_level_script_invalid(mocker):
    mocker.patch("nodeorc.water_level.execute_water_level_script", side_effect=Exception("Script execution failed"))
    with pytest.raises(ValueError, match="Error while validating script .*"):
        WaterLevel(script="invalid_script.py")


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


def test_water_level__ts_no_level(session):
    with pytest.raises(IntegrityError):
        wl = WaterLevelTimeSeries()
        session.add(wl)
        session.commit()


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
