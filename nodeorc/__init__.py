"""NodeORC: Automated edge and cloud image-based discharge estimation with OpenRiverCam"""
import os
__version__ = "0.1.2"

__home__ = os.path.join(os.path.expanduser("~"), ".nodeorc")
if not(os.path.isdir(__home__)):
    os.makedirs(__home__)

settings_path = os.path.join(os.getcwd(), "settings")

from . import tasks
from . import log
from . import models
from . import callbacks
from . import disk_mng
from . import db
from . import config

