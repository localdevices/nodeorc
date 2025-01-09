import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base, AlchemyEncoder, sqlalchemy_to_dict
from .active_config import ActiveConfig
from .callback import Callback
from .callback_url import CallbackUrl
from .device import Device, DeviceStatus, DeviceFormStatus
from .disk_management import DiskManagement
from .settings import Settings
from .storage import Storage
from .task_form import TaskForm, TaskFormStatus
from .water_level_settings import WaterLevelSettings
from .water_level_timeseries import WaterLevelTimeSeries

from nodeorc import __home__

db_path_config = os.path.join(
    __home__, "nodeorc_config.db"
)
engine_config = create_engine(f"sqlite:///{db_path_config}")

# make the models
Base.metadata.create_all(engine_config)

Session = sessionmaker()
Session.configure(bind=engine_config)
session = Session()

# if no device id is present, then create one
device_query = session.query(Device)
if len(device_query.all()) == 0:
    device = Device()
    session.add(device)
    session.commit()
