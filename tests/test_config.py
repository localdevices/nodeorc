# Tests for config objects
from nodeorc.models import LocalConfig
from nodeorc import db

from pydantic import ValidationError



def test_local_config(
        settings,
        callback_url,
        storage,
):

    local_config = LocalConfig(
        settings=settings,
        callback_url=callback_url,
        storage=storage,
    )
    print("success")


def test_add_config(session, config):
    """
    Test writing of record to database

    Parameters
    ----------
    session
    config

    Returns
    -------

    """
    config.add_config(session, config, set_as_active=False)
    # check if a record has been created (without an active record
    assert(len(session.query(db.models.Settings).all()) == 1)
    # check also if a active record has been created
    assert(len(session.query(db.models.ActiveConfig).all()) == 0)

    config.add_config(session, config, set_as_active=True)
    # check if two records have been created with an active record
    assert(len(session.query(db.models.Settings).all()) == 2)
    # check also if a active record has been created
    assert(len(session.query(db.models.ActiveConfig).all()) == 1)
    print("check")

    config.add_config(session, config, set_as_active=True)
    # check if two records have been created with an active record
    assert(len(session.query(db.models.Settings).all()) == 3)
    # check also if a active record has been created
    assert(len(session.query(db.models.ActiveConfig).all()) == 1)
    assert(session.query(db.models.ActiveConfig).first().settings_id == 3)
    config_record = config.get_active_config()
    # turn record into a dict
    # config_dict = dict(config_record.__dict__)
    config_retr = config.get_active_config(parse=True)
    # # remove id and _sa_instance_state
    # config_dict.pop("_sa_instance_state")
    # config_dict.pop("id")
    # # convert into a Config object
    # config_retr = LocalConfig(**config_dict)
    assert(config.model_dump() == config_retr.model_dump())
    d = config_retr.model_dump()
    # test if a bad config returns and error
    # d["water_level_fmt"] = "water_level/wl_{dummy}.csv"
    d["settings"].pop("water_level_fmt")
    try:
        c = LocalConfig(**d)
    except ValidationError as e:
        print(f"Found validation error {e}")

    d = config_retr.model_dump()
    storage = d.pop("storage")
    d["storag"] = storage
    try:
        c = LocalConfig(**d)
    except ValidationError as e:
        print(f"Found validation error {e}")


