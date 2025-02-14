import datetime
import os
import subprocess
from unittest.mock import Mock
import pytest
from nodeorc.water_level import execute_water_level_script


def test_execute_script_valid_output(monkeypatch):
    # Mock subprocess.check_output to simulate valid script output
    def mock_check_output(script_path, shell, capture_output):
        return mock_output

    mock_output = Mock()
    mock_output.stdout = b"2023-11-01T12:34:56Z,45.67\n"
    mock_output.returncode = 0  # Mimic a successful execution

    monkeypatch.setattr(subprocess, "run", mock_check_output)

    result = execute_water_level_script("dummy_script.sh", script_type="BASH")
    assert isinstance(result, tuple)
    assert isinstance(result[0], datetime.datetime)
    assert result[0] == datetime.datetime(2023, 11, 1, 12, 34, 56)
    assert isinstance(result[1], float)
    assert result[1] == 45.67


def test_execute_script_invalid_format(monkeypatch):
    # Mock subprocess.check_output to simulate invalid result format
    def mock_check_output(script_path, shell, capture_output=True):
        return mock_output
    mock_output = Mock()
    mock_output.stdout = b"INVALID_OUTPUT\n"
    mock_output.returncode = 0  # Mimic a successful execution

    monkeypatch.setattr(subprocess, "run", mock_check_output)

    with pytest.raises(ValueError, match="Invalid result format"):
        execute_water_level_script("dummy_script.sh", script_type="BASH")


def test_execute_script_invalid_datetime(monkeypatch):
    # Mock subprocess.check_output to simulate invalid datetime in the output
    def mock_check_output(script_path, shell, capture_output=True):
        return mock_output
    mock_output = Mock()
    mock_output.stdout = b"INVALID_DATETIME,45.67\n"
    mock_output.returncode = 0

    monkeypatch.setattr(subprocess, "run", mock_check_output)

    with pytest.raises(ValueError, match="Invalid result format"):
        execute_water_level_script("dummy_script.sh", script_type="BASH")


def test_execute_script_invalid_float(monkeypatch):
    # Mock subprocess.check_output to simulate invalid float in the output
    def mock_check_output(script_path, shell, capture_output=True):
        return mock_output
    mock_output = Mock()
    mock_output.stdout = b"2023-11-01T12:34:56Z,INVALID_FLOAT\n"
    mock_output.returncode = 0


    monkeypatch.setattr(subprocess, "run", mock_check_output)

    with pytest.raises(ValueError, match="Invalid result format"):
        execute_water_level_script("dummy_script.sh", script_type="BASH")


def test_execute_script_failed_execution(monkeypatch):
    # Mock subprocess.check_output to simulate script execution failure
    def mock_check_output(script_path, text, capture_output=True):
        # Simulate a CalledProcessError
        raise subprocess.CalledProcessError(returncode=1, cmd=script_path, output="Script failed")

    monkeypatch.setattr(subprocess, "run", mock_check_output)

    with pytest.raises(subprocess.CalledProcessError):
        execute_water_level_script("dummy_script.sh", script_type="PYTHON")


def test_execute_script_real_file(script="./dummy_script.sh"):
    print(os.path.abspath(script))
    result = execute_water_level_script(script, script_type="BASH")
    print(result)

