"""Unit tests for database models."""
import datetime
import json
import pytest
from nodeorc.db.models import WaterLevel, BaseData, Callback
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


def test_water_level_creation(session):
    timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
    level = 5.0
    water_level = WaterLevel(timestamp=timestamp, level=level)

    session.add(water_level)
    session.commit()

    retrieved = session.query(WaterLevel).first()
    assert retrieved is not None
    assert retrieved.timestamp == timestamp
    assert retrieved.level == level


def test_water_level_default_timestamp(session):
    level = 4.2
    water_level = WaterLevel(level=level)

    session.add(water_level)
    session.commit()

    retrieved = session.query(WaterLevel).first()
    assert retrieved is not None
    assert isinstance(retrieved.timestamp, datetime.datetime)
    assert retrieved.level == level


def test_water_level_no_level(session):
    with pytest.raises(IntegrityError):
        wl = WaterLevel()
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
