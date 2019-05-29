from .core import *
import sys, os

if sys.platform in ('win32', 'win64'):
    home_dir = os.getenv('userprofile')
    sessions_dir = os.path.join(home_dir, 'Documents\\aspy')
    if not os.path.exists(sessions_dir):
        os.mkdir(sessions_dir)
    else:
        pass

name = "aspy"
__version__ = "1.0b1"
