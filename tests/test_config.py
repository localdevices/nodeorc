# Tests for config objects
import db.config
from nodeorc.models import LocalConfig

def test_local_config(
        callback_url,
        storage,
        incoming_path,
        success_path,
        failed_path,
        results_path
):

    local_config = LocalConfig(
        callback_url=callback_url,
        storage=storage,
        incoming_path=incoming_path,
        failed_path=failed_path,
        success_path=success_path,
        results_path=results_path,
        parse_dates_from_file=True,
        video_file_fmt="video_{%Y%m%dT%H%M%S}.mp4",
        water_level_fmt="water_level/wl_{%Y%m%d}.csv",
        water_level_datetimefmt="%Y%m%dT%H%M%S",
        allowed_dt=1800
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
    db.config.add_config(session, config, set_as_active=False)
    # check if a record has been created (without an active record
    assert(len(session.query(db.models.Config).all()) == 1)

    # check also if a active record has been created
