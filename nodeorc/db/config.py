import models
from nodeorc.models import LocalConfig, RemoteConfig
from typing import Union
import json
import nodeorc.db.models as db_models
import sqlalchemy

def add_config(
        session: sqlalchemy.orm.session.Session,
        config: [LocalConfig, RemoteConfig],
        set_as_active=True
):
    """
    Add a configuration as new record to Config table

    Parameters
    ----------
    session
    config
    set_as_active

    Returns
    -------

    """
    config_dict = json.loads(config.to_json())
    config_record = db_models.Config(**config_dict)
    session.add(config_record)
    session.commit()
    print(config_record)
    if set_as_active:
        add_replace_active_config(session, config_record)

    return config_record


def add_replace_active_config(
        session,
        config_record
):
    """
    Set config as the currently active config

    Parameters
    ----------
    session
    config_record

    Returns
    -------

    """
    active_configs = session.query(db_models.ActiveConfig)
    if len(active_configs.all()) == 0:
        # no active config yet, make a new one
        active_config_record = db_models.ActiveConfig(config_id=config_record.id)
        session.add(active_config_record)
    else:
        # active config already exists, replace config
        active_config_record = active_configs.first()
        active_config_record.config_id = config_record.id
    session.commit()

def get_config(config_record):
    """
    Get a Config pydantic object from a stored db model

    Parameters
    ----------
    config_record : db.models.Config
        configuration

    Returns
    -------

    """
    config_dict =dict(config_record.__dict__)
    # remove id and _sa_instance_state
    config_dict.pop("_sa_instance_state")
    config_dict.pop("id")
    # convert into a Config object
    return models.LocalConfig(**config_dict)
