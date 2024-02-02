import os
from datetime import datetime

REMOVE_FOR_TEMPLATE = ["input_files", "id", "timestamp", "callback_url", "storage"]

def check_datetime_fmt(fn_fmt):
    # check string within {}, see if that can be parsed to datetime
    if not("{" in fn_fmt and "}" in fn_fmt):
        return True
    try:
        fmt = fn_fmt.split('{')[1].split('}')[0]
    except:
        raise ValueError('{:s} does not contain a datetime format between {""} signs'.format(fn_fmt))
    datestr = datetime(2000, 1, 1, 1, 1, 1).strftime(fmt)
    dt = datetime.strptime(datestr, fmt)
    if dt.year != 2000 or dt.month != 1 or dt.day != 1:
        raise ValueError(f'Date format "{fmt}" is not a valid date format pattern')
    return True

from .storage import Storage, S3Storage, File
from .callback_url import CallbackUrl
from .callback import Callback
from .subtask import Subtask
from .task import Task
from .config import LocalConfig, RemoteConfig, DiskManagement, Settings

