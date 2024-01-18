from nodeorc.models import LocalConfig, RemoteConfig
from typing import Union
import json
import nodeorc.db.models as db_models


def add_config(
        session,
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
    return config_record