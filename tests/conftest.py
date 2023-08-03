import json
import os
import pyorc
import pytest
import requests
import yaml

from datetime import datetime
from io import BytesIO, StringIO
from nodeorc import models, utils, log

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
    return os.path.abspath("./tmp")

@pytest.fixture
def s3_video_sample(video_sample_url, crossection_url, storage):
    # upload a video sample to s3 bucket
    filename = os.path.split(video_sample_url)[-1]
    filename_cs = os.path.split(crossection_url)[-1]
    print(f"Downloading {video_sample_url}")
    r = requests.get(video_sample_url)
    obj = BytesIO(r.content)
    print(f"Uploading {video_sample_url}")
    r = storage.upload_io(obj, dest=filename)
    # r = utils.upload_file(obj, storage.bucket[1], dest=filename)
    print(f"Downloading {crossection_url}")
    r = requests.get(crossection_url)
    obj = BytesIO(r.content)
    print(f"Uploading {crossection_url}")
    r = storage.upload_io(obj, dest=filename_cs)

    yield storage, filename, filename_cs
    print(f"Deleting {os.path.split(video_sample_url)[-1]}")
    storage.bucket.objects.filter(Prefix=filename).delete()

@pytest.fixture
def callback_url():
    return "127.0.0.1:1080"


@pytest.fixture
def storage():
    obj = models.Storage(
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id="admin",
        aws_secret_access_key="password",
        bucket_name="examplevideo"
    )
    return obj


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
def output_file(storage):
    obj = models.File(
        remote_name="piv.nc",
        tmp_name="OUTPUT/piv.nc",
    )
    return obj


@pytest.fixture
def subtask(callback, input_file, output_file, kwargs_piv):
    obj = models.Subtask(
        name="velocity_flow",
        kwargs=kwargs_piv,
        callback=callback,
        input_files={"videofile": input_file},
        output_files={"piv": output_file}
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
def task(callback_url, storage, subtask, input_file, input_file_cs, logger):
    obj = models.Task(
        time=datetime.now(),
        callback_url=callback_url,
        storage=storage,
        subtasks=[subtask],
        input_files=[input_file, input_file_cs],
        logger=logger
        # files that are needed to perform any subtask
    )
    return obj

