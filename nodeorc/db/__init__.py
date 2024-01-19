import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from . import config
from . import active_config
from nodeorc import __home__

db_path = os.path.join(
    __home__, "nodeorc.db"
)

engine = create_engine(f"sqlite:///{db_path}")

# make the models
Base.metadata.create_all(engine)

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

