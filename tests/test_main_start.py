# File: tests/test_main2.py

import pytest
from click.testing import CliRunner
from nodeorc.main import start

import pytest
from nodeorc import db


@pytest.fixture
def runner():
    return CliRunner()


def test_start_successful_execution(runner, session_config, monkeypatch):
    def mock_request_task_form(*args, **kwargs):
        return {"task_form": "dummy"}
    def mock_exit_code(*args, **kwargs):
        return 0
    # monkey patch the get_session function, replace result by filled_db
    monkeypatch.setattr("nodeorc.db_ops.get_session", lambda: session_config)
    monkeypatch.setattr("nodeorc.tasks.task_form.request_task_form", mock_request_task_form)
    monkeypatch.setattr("os._exit", mock_exit_code)
    result = runner.invoke(start)
    assert result.exit_code == 0
    assert session_config.query(db.Device).count() == 1
    # assert "Device" in result.output
    # assert "is online to run video analyses" in result.output


def test_start_no_active_config_error(runner, mocker):
    mocker.patch("nodeorc.db_ops.get_active_config", return_value=None)
    result = runner.invoke(start)
    assert result.exit_code != 0
    assert "You do not yet have an active configuration." in result.output
    assert isinstance(result.exception, SystemExit)


def test_start_initialization_failure(runner, mocker):
    mocker.patch("nodeorc.db_ops.get_active_config", return_value={"dummy_config": True})
    # mocker.patch("nodeorc.db.init_basedata.get_data_session", side_effect=Exception("Initialization error"))
    result = runner.invoke(start)
    assert result.exit_code != 0
    assert "You do not yet have a water level configuration." in result.output
    assert isinstance(result.exception, SystemExit)


def test_start_invalid_task_form_error(runner, session_config, mocker, monkeypatch):
    monkeypatch.setattr("nodeorc.db_ops.get_session", lambda: session_config)
    # mocker.patch("nodeorc.config.get_active_config", return_value={"dummy_config": True, "callback_url": "http://localhost:8000/callback"})
    mocker.patch("nodeorc.db_ops.get_active_task_form", return_value={"task_form": "invalid"})
    # mocker.patch("nodeorc.config.get_water_level_config", return_value={"dummy_water_level_config": True})
    mocker.patch("nodeorc.models.Task", side_effect=Exception("Invalid Task Form"))
    # mocker.patch("nodeorc.utils.model_to_dict", return_value={"dummy_water_level_config": True})

    result = runner.invoke(start)
    assert result.exit_code != 0
    # assertion on result.output is not possible, because the process WILL continue with a broken task form

