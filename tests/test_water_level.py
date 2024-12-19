import datetime
import os
import subprocess

import pytest
from nodeorc.water_level import execute_water_level_script


def test_execute_script_valid_output(monkeypatch):
    # Mock subprocess.check_output to simulate valid script output
    def mock_check_output(script_path, shell, stderr, text):
        return "2023-11-01T12:34:56Z,45.67\n"

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)

    result = execute_water_level_script("dummy_script.sh")
    assert isinstance(result, tuple)
    assert isinstance(result[0], datetime.datetime)
    assert result[0] == datetime.datetime(2023, 11, 1, 12, 34, 56)
    assert isinstance(result[1], float)
    assert result[1] == 45.67


def test_execute_script_invalid_format(monkeypatch):
    # Mock subprocess.check_output to simulate invalid result format
    def mock_check_output(script_path, shell, stderr, text):
        return "INVALID_OUTPUT\n"

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)

    with pytest.raises(ValueError, match="Invalid result format"):
        execute_water_level_script("dummy_script.sh")


def test_execute_script_invalid_datetime(monkeypatch):
    # Mock subprocess.check_output to simulate invalid datetime in the output
    def mock_check_output(script_path, shell, stderr, text):
        return "INVALID_DATETIME,45.67\n"

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)

    with pytest.raises(ValueError, match="Invalid result format"):
        execute_water_level_script("dummy_script.sh")


def test_execute_script_invalid_float(monkeypatch):
    # Mock subprocess.check_output to simulate invalid float in the output
    def mock_check_output(script_path, shell, stderr, text):
        return "2023-11-01T12:34:56Z,INVALID_FLOAT\n"

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)

    with pytest.raises(ValueError, match="Invalid result format"):
        execute_water_level_script("dummy_script.sh")


def test_execute_script_failed_execution(monkeypatch):
    # Mock subprocess.check_output to simulate script execution failure
    def mock_check_output(script_path, shell, stderr, text):
        # Simulate a CalledProcessError
        raise subprocess.CalledProcessError(returncode=1, cmd=script_path, output="Script failed")

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)

    with pytest.raises(RuntimeError, match="Script execution failed: Script failed"):
        execute_water_level_script("dummy_script.sh")

def test_execute_script_real_file(script="dummy_script.sh"):
    print(os.path.abspath(script))
    result = execute_water_level_script(script)
    print(result)


@pytest.mark.parametrize(
    "script", [
        # "g_red_api_request.sh",
        "get_waterlevel_limburg.py"
    ]
)
def test_execute_script_gred(script):
    import os
    dt = datetime.datetime(year=2024, month=11, day=30, hour=0, minute=30, tzinfo=datetime.timezone.utc)
    os.environ["GRED_EMAIL"] = "winsemius@rainbowsensing.com"
    os.environ["GRED_PASSWORD"] = "Zu2CzKbBKjDCe9G"
    print(os.path.abspath(script))
    result = execute_water_level_script(script, dt=dt)
    print(result)
