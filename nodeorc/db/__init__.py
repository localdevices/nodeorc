import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from . import config
from . import active_config

db_path = os.path.join(
    os.path.split(__file__)[0], "nodeorc.db"
)

engine = create_engine(f"sqlite:///{db_path}")

# make the models
Base.metadata.create_all(engine)

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

