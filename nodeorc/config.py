from models import LocalConfig, RemoteConfig
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

    settings_record = db_models.Settings(**config_dict["settings"])
    disk_management_record = db_models.DiskManagement(**config_dict["disk_management"])
    storage_record = db_models.Storage(**config_dict["storage"])
    # callback_url_record = db_models.CallbackUrl(**config_dict["callback_url"])
    url = config.callback_url.model_dump()
    url["url"] = str(url["url"])
    callback_url_record = db_models.CallbackUrl(**url)
    session.add(settings_record)
    session.add(disk_management_record)
    session.add(storage_record)
    session.add(callback_url_record)

    # config_record = db_models.Config(**config_dict)
    # session.add(config_record)
    session.commit()
    if set_as_active:
        active_config_record = add_replace_active_config(
            session,
            settings_record=settings_record,
            disk_management_record=disk_management_record,
            storage_record=storage_record,
            callback_url_record=callback_url_record
        )
        return active_config_record


def add_replace_active_config(
        session,
        settings_record=None,
        disk_management_record=None,
        storage_record=None,
        callback_url_record=None
):
    """
    Set config as the currently active config
    """
    active_configs = session.query(db_models.ActiveConfig)
    if len(active_configs.all()) == 0:
        # check if all records are present
        assert(
                None not in [
            settings_record,
            disk_management_record,
            storage_record,
            callback_url_record
        ]
        ), "No active configuration available yet, you need to supply settings, disk_management, storage and callback_url in your configuration. One or more are missing."
        # no active config yet, make a new one
        active_config_record = db_models.ActiveConfig(
            settings_id=settings_record.id,
            disk_management_id=disk_management_record.id,
            storage_id=storage_record.id,
            callback_url_id=callback_url_record.id,
        )
        session.add(active_config_record)
    else:
        # active config already exists, replace config
        active_config_record = get_active_config(session)
        if settings_record:
            active_config_record.settings = settings_record
            # active_config_record.settings_id = settings_record.id
        if disk_management_record:
            active_config_record.disk_management = disk_management_record
        if storage_record:
            active_config_record.storage = storage_record
        if callback_url_record:
            active_config_record.callback_url = callback_url_record
        # session.add(active_config_record)
    session.commit()
    return active_config_record

def get_settings(session, id):
    """
    Get a Config pydantic object from a stored db model

    Parameters
    ----------
    config_record : db.models.Config
        configuration

    Returns
    -------

    """
    return session.query(db_models.Settings).get(id)

def get_active_config(session, parse=False):
    active_configs = session.query(db_models.ActiveConfig)
    assert(len(active_configs.all()) == 1),\
        'You do not yet have an active configuration. Upload an activate configuration through the CLI. Type "nodeorc upload-config --help" for more information'
    active_config = active_configs.first()
    if parse:
        # parse into a Config object (TODO, also add RemoteConfig options)
        config_dict = {}
        for attr in ["settings", "storage", "callback_url", "disk_management"]:
            c = getattr(active_config, attr).__dict__
            c.pop("_sa_instance_state")
            c.pop("id")
            config_dict[attr] = c
        return LocalConfig(**config_dict)
    return active_config