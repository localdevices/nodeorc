"""NodeORC: Automated edge and cloud image-based discharge estimation with OpenRiverCam"""
import os
__version__ = "0.2.4"

__home__ = os.getenv("NODEORC_HOME")

if not __home__:
    __home__ = os.path.join(os.path.expanduser("~"), ".nodeorc")
if not(os.path.isdir(__home__)):
    os.makedirs(__home__)

settings_path = os.path.join(os.getcwd(), "settings")
