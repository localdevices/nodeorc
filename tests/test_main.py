# File: tests/test_main2.py

import os
import time

import pytest
from click.testing import CliRunner
from nodeorc.main import upload_water_level_script
from nodeorc.db.models import WaterLevel
from nodeorc.db import db_path_config

# @pytest.fixture
def get_session_config():
    from nodeorc.db import session
    return session


def test_upload_water_level_script_success(tmp_path):
    """Test successful execution of upload_water_level_script with valid inputs."""
    session_config = get_session_config()
    test_script_path = tmp_path / "test_script.py"
    test_script_path.write_text("print('2023-11-01T12:34:56Z,78.90')")

    runner = CliRunner()
    result = runner.invoke(
        upload_water_level_script,
        [
            "--script", str(test_script_path),
            "--script-type", "python",
            "--file-template", "wl_{%Y%m%d}.txt",
            "--frequency", "600",
            "--datetime-fmt", "%Y-%m-%dT%H:%M:%SZ",
        ]
    )
    # check if record was indeed added
    record = session_config.query(WaterLevel).all()
    assert len(record) == 1

    assert result.exit_code == 0
    assert "Created new WaterLevel record with" in result.output
    if os.path.exists(db_path_config):
        os.unlink(db_path_config)

def test_upload_water_level_script_missing_script():
    """Test failure when the script file is not provided."""
    runner = CliRunner()
    result = runner.invoke(
        upload_water_level_script,
        [
            "--file-template", "wl_{%Y%m%d}.txt",
            "--frequency", "600",
            "--datetime-fmt", "%Y-%m-%dT%H:%M:%SZ",
        ]
    )

    assert result.exit_code == 2
    assert "Error: Missing option '-s' / '--script'" in result.output
    if os.path.exists(db_path_config):
        os.unlink(db_path_config)


def test_upload_water_level_script_invalid_file_template(tmp_path):
    """Test failure when the file template is invalid."""
    test_script_path = tmp_path / "test_script.py"
    test_script_path.write_text("print('test script')")

    runner = CliRunner()
    result = runner.invoke(
        upload_water_level_script,
        [
            "--script", str(test_script_path),
            "--script-type", "python",
            "--file-template", "invalid_template",
            "--frequency", "600",
            "--datetime-fmt", "%Y-%m-%dT%H:%M:%SZ",
        ]
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    if os.path.exists(db_path_config):
        os.unlink(db_path_config)


def test_upload_water_level_script_invalid_frequency(tmp_path):
    """Test failure when the frequency value is invalid."""
    test_script_path = tmp_path / "test_script.py"
    test_script_path.write_text("print('2023-11-01T12:34:56Z,78.90')")

    runner = CliRunner()
    result = runner.invoke(
        upload_water_level_script,
        [
            "--script", str(test_script_path),
            "--script-type", "python",
            "--file-template", "wl_{%Y%m%d}.txt",
            "--frequency", "-10",
            "--datetime-fmt", "%Y-%m-%dT%H:%M:%SZ",
        ]
    )

    assert result.exit_code != 0
    assert "Invalid value for '-fr' / '--frequency'" in result.output
    if os.path.exists(db_path_config):
        os.unlink(db_path_config)


def test_upload_water_level_script_invalid_datetime_format(tmp_path):
    """Test failure when the datetime format is invalid."""
    test_script_path = tmp_path / "test_script.py"
    test_script_path.write_text("print('2023-11-01T12:34:56Z,78.90')")

    runner = CliRunner()
    result = runner.invoke(
        upload_water_level_script,
        [
            "--script", str(test_script_path),
            "--script-type", "python",
            "--file-template", "wl_{%Y%m%d}.txt",
            "--frequency", "600",
            "--datetime-fmt", "invalid_format",
        ]
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    if os.path.exists(db_path_config):
        os.unlink(db_path_config)
