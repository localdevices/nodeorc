# File: tests/test_main2.py

import pytest
from click.testing import CliRunner
from nodeorc.main import start

import pytest
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from nodeorc.db import models as db_models, Session  # Adjust imports based on your project's structure

# engine = create_engine("sqlite:///:memory:")
# BaseData.metadata.create_all(engine)
# Session = sessionmaker(bind=engine)
# session = Session()
# yield session


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
    # session.commit()

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
        disk_management_instance = db_models.DiskManagement()
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
def runner():
    return CliRunner()


def test_start_successful_execution(runner, session_config, monkeypatch):
    def mock_request_task_form(*args, **kwargs):
        return {"task_form": "dummy"}
    def mock_exit_code(*args, **kwargs):
        return 0
    # monkey patch the get_session function, replace result by filled_db
    monkeypatch.setattr("nodeorc.main.get_session", lambda: session_config)
    monkeypatch.setattr("nodeorc.tasks.task_form.request_task_form", mock_request_task_form)
    monkeypatch.setattr("os._exit", mock_exit_code)
    result = runner.invoke(start)
    assert result.exit_code == 0
    assert session_config.query(db_models.Device).count() == 1
    # assert "Device" in result.output
    # assert "is online to run video analyses" in result.output


def test_start_no_active_config_error(runner, mocker):
    mocker.patch("nodeorc.config.get_active_config", return_value=None)
    result = runner.invoke(start)
    assert result.exit_code != 0
    assert "You do not yet have an active configuration." in result.output
    assert isinstance(result.exception, SystemExit)


def test_start_initialization_failure(runner, mocker):
    mocker.patch("nodeorc.config.get_active_config", return_value={"dummy_config": True})
    # mocker.patch("nodeorc.db.init_basedata.get_data_session", side_effect=Exception("Initialization error"))
    result = runner.invoke(start)
    assert result.exit_code != 0
    assert "You do not yet have a water level configuration." in result.output
    assert isinstance(result.exception, SystemExit)


def test_start_invalid_task_form_error(runner, session_config, mocker, monkeypatch):
    monkeypatch.setattr("nodeorc.main.get_session", lambda: session_config)
    # mocker.patch("nodeorc.config.get_active_config", return_value={"dummy_config": True, "callback_url": "http://localhost:8000/callback"})
    mocker.patch("nodeorc.config.get_active_task_form", return_value={"task_form": "invalid"})
    # mocker.patch("nodeorc.config.get_water_level_config", return_value={"dummy_water_level_config": True})
    mocker.patch("nodeorc.models.Task", side_effect=Exception("Invalid Task Form"))
    # mocker.patch("nodeorc.utils.model_to_dict", return_value={"dummy_water_level_config": True})

    result = runner.invoke(start)
    assert result.exit_code != 0
    # assertion on result.output is not possible, because the process WILL continue with a broken task form

