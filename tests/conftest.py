import os
import pytest
import requests

from datetime import datetime
from io import BytesIO
from nodeorc import models, utils

@pytest.fixture
def video_sample_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere_20191103.mp4"


@pytest.fixture
def s3_video_sample(video_sample_url, storage):
    # upload a video sample to s3 bucket
    filename = os.path.split(video_sample_url)[-1]
    print(f"Downloading {video_sample_url}")
    r = requests.get(video_sample_url)
    obj = BytesIO(r.content)
    print(f"Uploading {video_sample_url}")
    r = utils.upload_file(obj, storage.bucket[1], dest=filename)
    yield storage.bucket[1], filename
    print(f"Deleting {os.path.split(video_sample_url)[-1]}")
    storage.bucket[1].objects.filter(Prefix=filename).delete()

@pytest.fixture
def callback_url():
    return "http://api.globalwaterwatch.earth"


@pytest.fixture
def storage():
    obj = models.Storage(
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id="admin",
        aws_secret_access_key="password",
        bucket_name="examplevideo"
    )
    return obj

    task = nodeorc.models.Task(
        storage={"endpoint_url": s3_url},
        callback_url={"url": callback_url},

        # callbacks = [callback]
    )


@pytest.fixture
def callback_url():
    obj = models.CallbackUrl(
        url="http://127.0.0.1:1080",
        token=None
    )
    return obj

@pytest.fixture
def callback():
    obj = models.Callback(
        func_name="post_discharge",
        kwargs={},
        url_subpath="http://127.0.0.1:1080/discharge"  # used to extend the default callback url
    )
    return obj

@pytest.fixture
def input_file(video_sample_url, storage):
    video_sample_file = os.path.split(video_sample_url)[-1]
    obj = models.InputFile(
        remote_name="video.mp4",
        tmp_name="video.mp4",
        storage=storage
    )
    return obj

@pytest.fixture
def output_file(storage):
    obj = models.OutputFile(
        remote_name="piv.nc",
        tmp_name="OUTPUT/piv.nc",
        storage=storage
    )
    return obj


@pytest.fixture
def subtask(callback, input_file, output_file):
    obj = models.Subtask(
        name="VelocityFlowProcessor",
        kwargs={},
        callback=callback,
        input_files={"videofile": input_file},
        output_files={"piv": output_file}
    )
    return obj

@pytest.fixture
def task(callback_url, storage, subtask, input_file):
    obj = models.Task(
        time=datetime.now(),
        callback_url=callback_url,
        storage=storage,
        subtasks=[subtask],
        input_files=[input_file]  # files that are needed to perform any subtask
    )
    return obj

