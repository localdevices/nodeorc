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
        active_config_record = get_active_config(session)
        print(f"ID: {config_record.id}")
        active_config_record.config_id = config_record.id
        session.add(active_config_record)
    session.commit()

def get_config(session, id):
    """
    Get a Config pydantic object from a stored db model

    Parameters
    ----------
    config_record : db.models.Config
        configuration

    Returns
    -------

    """
    return session.query(db_models.Config).get(id)

def get_active_config(session):
    active_configs = session.query(db_models.ActiveConfig)
    assert(len(active_configs.all()) == 1),\
        'You do not yet have an active configuration. Upload an activate configuration through the CLI. Type "nodeorc new_settings --help" for more information'
    return active_configs.first().config