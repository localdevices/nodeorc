import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Device
from . import active_config
from .. import __home__

db_path = os.path.join(
    __home__, "nodeorc.db"
)

engine = create_engine(f"sqlite:///{db_path}")

# make the models
Base.metadata.create_all(engine)

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

# if no device id is present, then create one
device_query = session.query(Device)
if len(device_query.all()) == 0:
    device = Device()
    session.add(device)
    session.commit()
