import os
import pytest

from click.testing import CliRunner
from nodeorc.main import upload_config
from nodeorc.db import models as db_models

@pytest.fixture
def config_file(tmpdir):
    json_str = """
    {
        "callback_url": {
            "url": "http://framework:8000",
            "token_refresh_end_point": "/api/token/refresh/",
            "token_refresh": "somekey",
            "token_access": "somekey"
        },
        "storage": {
            "url": "./tmp",
            "bucket_name": "examplevideo"
        },
        "settings": {
            "parse_dates_from_file": true,
            "video_file_fmt": "{%Y%m%d_%H%M%S}.mp4",
            "allowed_dt": 3600,
            "shutdown_after_task": false,
            "reboot_after": 86400
        },
        "disk_management": {
            "home_folder":""" + str('"' + str(tmpdir) + '"') + """,
            "min_free_space": 2,
            "critical_space": 1,
            "frequency": 3600
        }
    }
    """
    config_file = tmpdir / "test_config.json"
    with open(config_file, "w") as f:
        f.write(json_str)

    yield config_file
    os.remove(config_file)

def test_load_config(config_file):
    from nodeorc.main import load_config
    config = load_config(config_file)
    assert config["callback_url"]["url"] == "http://framework:8000"
    assert config["storage"]["url"] == "./tmp"
    assert config["settings"]["parse_dates_from_file"] == True
    assert config["disk_management"]["min_free_space"] == 2


@pytest.fixture
def runner():
    return CliRunner()


def test_start_successful_execution(runner, session_empty, config_file, monkeypatch):
    monkeypatch.setattr("nodeorc.db_ops.get_session", lambda: session_empty)
    result = runner.invoke(upload_config, [str(config_file)])
    assert result.exit_code == 0
    assert session_empty.query(db_models.Settings).count() == 1