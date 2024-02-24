from .models import ActiveConfig
def active_config_available(session):
    """
    Returns if an active configuration already exists (True) or not (False)

    Parameters
    ----------
    session

    Returns
    -------

    """
    q = session.query(ActiveConfig)
    return len(q) > 0


