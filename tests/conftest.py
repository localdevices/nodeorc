import json
import os
import pika
import pyorc
import pytest
import requests
import shutil
import yaml

# database specific imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime
from io import BytesIO, StringIO
from nodeorc import models, utils, log
from nodeorc.db.models import Base


def prep_video_sample(video_sample_url, storage):
    filename = os.path.split(video_sample_url)[-1]
    print(f"Downloading {video_sample_url}")
    r = requests.get(video_sample_url)
    obj = BytesIO(r.content)
    print(f"Uploading {video_sample_url}")
    storage.upload_io(obj, dest=filename)
    return storage, filename


@pytest.fixture
def incoming_path():
    path = "incoming"
    if not os.path.isdir(path):
        os.makedirs(path)
    yield path
    shutil.rmtree(path)

@pytest.fixture
def failed_path():
    path = "failed"
    if not os.path.isdir(path):
        os.makedirs(path)
    yield path
    shutil.rmtree(path)

@pytest.fixture
def success_path():
    path = "success"
    if not os.path.isdir(path):
        os.makedirs(path)
    yield path
    shutil.rmtree(path)

@pytest.fixture
def results_path():
    path = "results"
    if not os.path.isdir(path):
        os.makedirs(path)
    yield path
    shutil.rmtree(path)


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
def output_nc():
    return os.path.join(os.path.dirname(__file__), "examples", "ngwerere_transect.nc")

@pytest.fixture
def crossection(crossection_url):
    r = requests.get(crossection_url)
    obj = BytesIO(r.content)
    obj.seek(0)
    return json.load(obj)



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
def recipe(recipe_url, crossection):
    r = requests.get(recipe_url)
    recipe = yaml.load(r.text, Loader=yaml.FullLoader)
    # use the validation scheme of pyorc to validate the recipe
    recipe = pyorc.cli.cli_utils.validate_recipe(recipe)
    # replace the location of the cross section file by an already read geojson
    recipe["transect"]["transect_1"]["geojson"] = crossection
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
def s3_video_sample(video_sample_url, s3storage):
    # upload a video sample to s3 bucket
    s3storage, filename = prep_video_sample(video_sample_url, s3storage)
    yield s3storage, filename
    print(f"Deleting {os.path.split(video_sample_url)[-1]}")
    s3storage.bucket.objects.filter(Prefix=filename).delete()

@pytest.fixture
def local_video_sample(video_sample_url, storage):
    storage, filename = prep_video_sample(video_sample_url, storage)
    yield storage, filename
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
def settings(
        incoming_path,
        failed_path,
        success_path,
        results_path
):
    return models.Settings(
        incoming_path=incoming_path,
        failed_path=failed_path,
        success_path=success_path,
        results_path=results_path,
        parse_dates_from_file=True,
        video_file_fmt="video_{%Y%m%dT%H%M%S}.mp4",
        water_level_fmt="water_level/wl_{%Y%m%d}.csv",
        water_level_datetimefmt="%Y%m%dT%H%M%S",
        allowed_dt=1800
    )


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
def callback(output_nc):
    obj = models.Callback(
        file=models.File(
            tmp_name=os.path.split(output_nc)[1],
            remote_name=os.path.split(output_nc)[1]
        ),
        func_name="discharge",
        kwargs={},
        storage=models.Storage(
            url="",
            bucket_name=os.path.split(output_nc)[0]
        ),
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
    storage, filename = s3_video_sample
    obj = models.File(
        remote_name=filename,
        tmp_name="video.mp4",
    )
    return obj


@pytest.fixture
def input_file_local(local_video_sample):
    storage, filename = local_video_sample
    obj = models.File(
        remote_name=filename,
        tmp_name="video.mp4",
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
def subtask(callback, kwargs_piv):
    obj = models.Subtask(
        name="velocity_flow",
        kwargs=kwargs_piv,
        callbacks=[callback],
        input_files={"videofile": models.File()},
        output_files={"piv": models.File(), "transect": models.File()}
    )
    return obj


@pytest.fixture
def subtask_local(callback, kwargs_piv):
    obj = models.Subtask(
        name="velocity_flow",
        kwargs=kwargs_piv,
        callbacks=[callback],
        input_files={"videofile": models.File()},
        output_files={"piv": models.File(), "transect": models.File()}
    )
    return obj


@pytest.fixture
def kwargs_piv(camconfig, recipe, temp_path):
    kwargs = {
        "videofile": "video.mp4",
        "h_a": 0.0,
        "cameraconfig": camconfig,
        "recipe": recipe,
        "output": os.path.join(temp_path, "OUTPUT"),
        "prefix": ""
    }
    return kwargs



@pytest.fixture
def task(callback_url, s3storage, subtask, input_file, output_file, output_file_cs, logger):
    obj = models.Task(
        time=datetime.now(),
        callback_url=callback_url,
        storage=s3storage,
        subtasks=[subtask],
        input_files={"videofile": input_file},
        output_files={"piv": output_file, "transect": output_file_cs},
        logger=logger
        # files that are needed to perform any subtask
    )
    return obj

@pytest.fixture
def task_local(
        callback_url,
        storage,
        subtask_local,
        input_file_local,
        output_file,
        output_file_cs,
        logger
):
    obj = models.Task(
        time=datetime.now(),
        callback_url=callback_url,
        storage=storage,
        subtasks=[subtask_local],
        input_files={"videofile": input_file_local},
        output_files={"piv": output_file, "transect": output_file_cs},
        logger=logger
        # files that are needed to perform any subtask
    )
    return obj


@pytest.fixture
def config(
    settings,
    callback_url,
    storage,
):
    return models.LocalConfig(
        settings=settings,
        callback_url=callback_url,
        storage=storage,
    )


@pytest.fixture
def session():
    engine = create_engine(f"sqlite://")
    # make the models
    Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)
    return Session()

