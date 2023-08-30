import json
import os
import pika
import pyorc
import pytest
import requests
import yaml

from datetime import datetime
from io import BytesIO, StringIO
from nodeorc import models, utils, log


def prep_video_sample(video_sample_url, crossection_url, storage):
    filename = os.path.split(video_sample_url)[-1]
    filename_cs = os.path.split(crossection_url)[-1]
    print(f"Downloading {video_sample_url}")
    r = requests.get(video_sample_url)
    obj = BytesIO(r.content)
    print(f"Uploading {video_sample_url}")
    storage.upload_io(obj, dest=filename)
    print(f"Downloading {crossection_url}")
    r = requests.get(crossection_url)
    obj = BytesIO(r.content)
    print(f"Uploading {crossection_url}")
    storage.upload_io(obj, dest=filename_cs)
    return storage, filename, filename_cs


@pytest.fixture
def video_sample_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere_20191103.mp4"

@pytest.fixture
def recipe_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere.yml"


@pytest.fixture
def camconfig_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/ngwerere.json"


@pytest.fixture
def crossection_url():
    return "https://raw.githubusercontent.com/localdevices/pyorc/main/examples/ngwerere/cross_section1.geojson"


@pytest.fixture
def camconfig(camconfig_url):
    r = requests.get(camconfig_url)
    return r.json()

@pytest.fixture
def channel():
    connection = pika.BlockingConnection(
        pika.URLParameters(
            "amqp://admin:password@localhost:5672"
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue="processing")
    yield channel
    connection.close()


@pytest.fixture
def recipe(recipe_url, temp_path):
    r = requests.get(recipe_url)
    recipe = yaml.load(r.text, Loader=yaml.FullLoader)
    # use the validation scheme of pyorc to validate the recipe
    recipe = pyorc.cli.cli_utils.validate_recipe(recipe)
    # replace the location of the cross section file
    recipe["transect"]["transect_1"]["shapefile"] = os.path.join(temp_path, "crosssection.geojson")
    # we'll leave the second transect for simplicity
    del recipe["transect"]["transect_2"]
    del recipe["plot"]["plot_quiver"]["transect"]["transect_2"]
    return recipe


@pytest.fixture
def logger():
    return log.start_logger(True, False)


@pytest.fixture
def temp_path():
    return "./tmp"

@pytest.fixture
def s3_video_sample(video_sample_url, crossection_url, s3storage):
    # upload a video sample to s3 bucket
    s3storage, filename, filename_cs = prep_video_sample(video_sample_url, crossection_url, s3storage)
    # filename = os.path.split(video_sample_url)[-1]
    # filename_cs = os.path.split(crossection_url)[-1]
    # print(f"Downloading {video_sample_url}")
    # r = requests.get(video_sample_url)
    # obj = BytesIO(r.content)
    # print(f"Uploading {video_sample_url}")
    # r = s3storage.upload_io(obj, dest=filename)
    # # r = utils.upload_file(obj, storage.bucket[1], dest=filename)
    # print(f"Downloading {crossection_url}")
    # r = requests.get(crossection_url)
    # obj = BytesIO(r.content)
    # print(f"Uploading {crossection_url}")
    # r = s3storage.upload_io(obj, dest=filename_cs)
    #
    yield s3storage, filename, filename_cs
    print(f"Deleting {os.path.split(video_sample_url)[-1]}")
    storage.bucket.objects.filter(Prefix=filename).delete()

@pytest.fixture
def local_video_sample(video_sample_url, crossection_url, storage):
    storage, filename, filename_cs = prep_video_sample(video_sample_url, crossection_url, storage)
    yield storage, filename, filename_cs
    # at the end remove the entire bucket
    # storage.delete()


@pytest.fixture
def s3storage():
    obj = models.S3Storage(
        url="http://127.0.0.1:9000",
        bucket_name="examplevideo",
        options={
            "aws_access_key_id": "admin",
            "aws_secret_access_key": "password",
        }
    )
    return obj

@pytest.fixture
def storage():
    obj = models.Storage(
        url="./tmp",
        bucket_name="examplevideo"
    )
    return obj



@pytest.fixture
def callback_url():
    obj = models.CallbackUrl(
        url="http://127.0.0.1:1080",
        token=None,
        refresh_token=None,
    )
    return obj

@pytest.fixture
def callback_url_amqp():
    obj = models.CallbackUrl(
        url="http://mockserver:1080",
        token=None
    )
    return obj



@pytest.fixture
def callback():
    obj = models.Callback(
        func_name="discharge",
        kwargs={},
        endpoint="/api/timeseries/"  # used to extend the default callback url
    )
    return obj


@pytest.fixture
def callback_patch():
    obj = models.Callback(
        func_name="discharge",
        kwargs={},
        request_type="PATCH",
        endpoint="/api/timeseries/1"  # used to extend the default callback url
    )
    return obj


@pytest.fixture
def input_file(s3_video_sample, video_sample_url):
    storage, filename, filename_cs = s3_video_sample
    obj = models.File(
        remote_name=filename,
        tmp_name="video.mp4",
    )
    return obj


@pytest.fixture
def input_file_cs(s3_video_sample, crossection_url):
    storage, filename, filename_cs = s3_video_sample
    obj = models.File(
        remote_name=filename_cs,
        tmp_name="crosssection.geojson",
    )
    return obj

@pytest.fixture
def input_file_local(local_video_sample):
    storage, filename, filename_cs = local_video_sample
    obj = models.File(
        remote_name=filename,
        tmp_name="video.mp4",
    )
    return obj


@pytest.fixture
def input_file_cs_local(local_video_sample, crossection_url):
    storage, filename, filename_cs = local_video_sample
    obj = models.File(
        remote_name=filename_cs,
        tmp_name="crosssection.geojson",
    )
    return obj


@pytest.fixture
def output_file():
    obj = models.File(
        remote_name="piv.nc",
        tmp_name="OUTPUT/piv.nc",
    )
    return obj


@pytest.fixture
def output_file_cs():
    obj = models.File(
        remote_name="transect_transect_1.nc",
        tmp_name="OUTPUT/transect_transect_1.nc",
    )
    return obj


@pytest.fixture
def subtask(callback, input_file, output_file, output_file_cs, kwargs_piv):
    obj = models.Subtask(
        name="velocity_flow",
        kwargs=kwargs_piv,
        callback=callback,
        input_files={"videofile": input_file},
        output_files={"piv": output_file, "transect": output_file_cs}
    )
    return obj


@pytest.fixture
def subtask_local(callback, input_file_local, output_file, output_file_cs, kwargs_piv):
    obj = models.Subtask(
        name="velocity_flow",
        kwargs=kwargs_piv,
        callback=callback,
        input_files={"videofile": input_file_local},
        output_files={"piv": output_file, "transect": output_file_cs}
    )
    return obj


@pytest.fixture
def kwargs_piv(camconfig, recipe, temp_path):
    kwargs = {
        "videofile": "video.mp4",
        "cameraconfig": camconfig,
        "recipe": recipe,
        "output": os.path.join(temp_path, "OUTPUT"),
        "prefix": ""
    }
    return kwargs



@pytest.fixture
def task(callback_url, s3storage, subtask, input_file, input_file_cs, logger):
    obj = models.Task(
        time=datetime.now(),
        callback_url=callback_url,
        storage=s3storage,
        subtasks=[subtask],
        input_files=[input_file, input_file_cs],
        logger=logger
        # files that are needed to perform any subtask
    )
    return obj

@pytest.fixture
def task_local(callback_url, storage, subtask_local, input_file_local, input_file_cs_local, logger):
    obj = models.Task(
        time=datetime.now(),
        callback_url=callback_url,
        storage=storage,
        subtasks=[subtask_local],
        input_files=[input_file_local, input_file_cs_local],
        logger=logger
        # files that are needed to perform any subtask
    )
    return obj

