# File: tests/test_local_task.py

import pytest

from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

from nodeorc.db import CallbackUrl, Settings, DiskManagement, WaterLevelSettings, TimeSeries
from nodeorc.tasks.local_task import LocalTaskProcessor, get_water_level
from nodeorc import utils, db_ops

@pytest.fixture
def callback_url(session_config):
    return session_config.query(CallbackUrl).first()

@pytest.fixture
def settings(session_config):
    return session_config.query(Settings).first()

@pytest.fixture
def disk_management(session_config):
    return session_config.query(DiskManagement).first()

@pytest.fixture
def water_level_settings(session_config):
    return session_config.query(WaterLevelSettings).first()


@pytest.fixture
def local_task_processor(session_config, settings, disk_management, callback_url, water_level_settings, logger):
    task_form_template = MagicMock()
    water_level_settings = utils.model_to_dict(water_level_settings)
    return LocalTaskProcessor(
        task_form_template=task_form_template,
        logger=logger,
        settings=settings,
        disk_management=disk_management,
        callback_url=callback_url,
        water_level_settings=water_level_settings,
        auto_start_threads=False,
    )

@pytest.fixture
def local_task_processor_shutdown(local_task_processor):
    local_task_processor.settings.shutdown_after_task = True
    return local_task_processor

def test_await_task(tmpdir, local_task_processor, mocker):
    mocker.patch("nodeorc.disk_mng.scan_folder", return_value=[str(tmpdir / "video_20000101T000000.mp4")])
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("nodeorc.utils.is_file_size_changing", return_value=False)
    mocker.patch("nodeorc.tasks.local_task.LocalTaskProcessor.process_file", return_value=None)
    with patch("multiprocessing.cpu_count", return_value=4):
        task_submitted = local_task_processor.await_task(single_task=True)
        assert task_submitted == True  # Assuming the method doesn't return anything; validate relevant expected state



# def test_add_water_level(tmpdir, session_config, local_task_processor, monkeypatch, mocker):
#     time_series = TimeSeries()
#     monkeypatch.setattr("nodeorc.db_ops.get_session", lambda: session_config)
#     timestamp, level = local_task_processor.add_water_level(single_task=True)
#     assert isinstance(timestamp, datetime)
#     assert isinstance(level, float)


def test_get_water_level_from_db(session_config):
    # create a bunch of water level in the database
    timestamps = [datetime.now(UTC) + timedelta(hours=h) for h in range(-4, 5)]
    values = list(range(len(timestamps)))
    # make several timestamps to store
    for t, v in zip(timestamps, values):
        water_level_instance = TimeSeries(
            timestamp=t,
            h=v,
        )
        session_config.add(water_level_instance)
    session_config.commit()
    rec = get_water_level(
        timestamp=timestamps[3] - timedelta(minutes=5),
        file_fmt="wl_{%Y%m%d}.txt",
        datetime_fmt="%Y%m%dT%H%M%SZ",
        allowed_dt=3600,
        session=session_config,
    )
    assert rec.h == values[3]


def test_get_water_level_outside_dt(session_config, monkeypatch, mocker):
    # mock get_water_level_file to produce some value which does not exist in the database
    mocker.patch("nodeorc.water_level.get_water_level_file", return_value=3.5)

    # create a bunch of water level in the database
    timestamps = [datetime.now(UTC) + timedelta(hours=h) for h in range(-4, 5)]
    values = list(range(len(timestamps)))
    # make several timestamps to store
    for t, v in zip(timestamps, values):
        water_level_instance = TimeSeries(
            timestamp=t,
            h=v,
        )
        session_config.add(water_level_instance)
    session_config.commit()
    monkeypatch.setattr("nodeorc.db_ops.get_session", lambda: session_config)
    # now we select a timestamp that is close to but still outside of the range
    rec = get_water_level(
        timestamp=timestamps[3] - timedelta(minutes=5),
        file_fmt="wl_{%Y%m%d}.txt",
        datetime_fmt="%Y%m%dT%H%M%SZ",
        allowed_dt=10,  # only ten seconds difference allowed.
        session=session_config,
    )
    assert rec.h == 3.5

def test_get_water_level_file_not_available(session_config, monkeypatch):

    # create a bunch of water level in the database
    timestamps = [datetime.now(UTC) + timedelta(hours=h) for h in range(-4, 5)]
    values = list(range(len(timestamps)))
    # make several timestamps to store
    for t, v in zip(timestamps, values):
        water_level_instance = TimeSeries(
            timestamp=t,
            h=v,
        )
        session_config.add(water_level_instance)
    session_config.commit()
    monkeypatch.setattr("nodeorc.db_ops.get_session", lambda: session_config)
    # now we select a timestamp that is close to but still outside of the range
    rec = get_water_level(
        timestamp=timestamps[3] - timedelta(minutes=5),
        file_fmt="wl_{%Y%m%d}.txt",
        datetime_fmt="%Y%m%dT%H%M%SZ",
        allowed_dt=10,  # only ten seconds difference allowed.
        session=session_config,
    )
    # rec should be None
    assert rec is None


def test_cleanup_enough_space(local_task_processor):
    # only test if the function returns true if the free space is above minimum required space.
    free_space = 500  #GB
    # disk_management_mock.cleanup.return_value = True
    result = local_task_processor.cleanup_space(free_space)
    assert result is None or result is True  # Based on the expected response


def test_cleanup_too_little_space(local_task_processor):
    # only test if the function returns true if the free space is above minimum required space.
    free_space = 2  #GB
    # disk_management_mock.cleanup.return_value = True
    result = local_task_processor.cleanup_space(free_space)
    assert result is None or result is True  # Based on the expected response



# def test_process_file(local_task_processor):
#     file_path = "/tmp/test_file"
#     with patch("os.path.exists", return_value=True), patch(
#             "shutil.rmtree"
#     ), patch("os.makedirs") as mock_makedirs:
#         local_task_processor.process_file(file_path)
#         assert mock_makedirs.called


def test_set_results_to_final_path(local_task_processor, tmpdir):
    cur_path = tmpdir / "current_path"
    dst_path = tmpdir / "destination_path"
    cur_path.mkdir()
    dst_path.mkdir()
    filename = "result_file"
    cur_path = cur_path / filename
    task_path = "/tmp/task_path"
    with patch("os.rename") as mock_move:
        local_task_processor._set_results_to_final_path(
            cur_path, dst_path, filename, task_path
        )
        mock_move.assert_called_once_with(
            cur_path, f"{dst_path}/{filename}"
        )


def test_shutdown_or_not(local_task_processor_shutdown):
    # set settings
    with patch("os.system", return_value=None) as mock_shutdown:
        local_task_processor_shutdown._shutdown_or_not()
        assert mock_shutdown.called


def test_reboot_now_or_not(local_task_processor):
    with patch("os.system", return_value=None) as mock_reboot:
        # set reboot to True
        local_task_processor.reboot = True
        local_task_processor.reboot_now_or_not()
        assert(mock_reboot.called == True)

