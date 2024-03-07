import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import BaseData
from ..config import get_data_folder

data_folder = get_data_folder()

if data_folder:
    db_path_data = os.path.join(
        data_folder,
        "nodeorc_data.db"
    )
else:
    db_path_data = None


def get_data_session():
    if not db_path_data:
        raise ValueError("No configuration available yet, upload a configuration to database first")
    """ create/read the databse file for storing dynamic components """
    engine_data = create_engine(f"sqlite:///{db_path_data}")
    BaseData.metadata.create_all(engine_data)
    Session = sessionmaker()
    Session.configure(bind=engine_data)
    return Session()
