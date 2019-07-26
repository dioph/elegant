import logging
import os
import sys
import traceback

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from . import PACKAGEDIR


class LineSegment(object):
    def __init__(self, obj, coords, dlines, remove=False):
        self.coords = coords
        self.dlines = dlines
        self.obj = obj
        self.remove = remove


class GenericSignal(QObject):
    signal = pyqtSignal(object)

    def __init__(self):
        super(GenericSignal, self).__init__()

    def emit_sig(self, args):
        self.signal.emit(args)


def getSessionsDir():
    if sys.platform in ('win32', 'win64'):
        home_dir = os.getenv('userprofile')
        sessions_dir = os.path.join(home_dir, 'Documents\\aspy')
    elif sys.platform == 'linux':
        home_dir = os.getenv('HOME')
        sessions_dir = os.path.join(home_dir, 'aspy')
    else:
        sessions_dir = '.'
    if not os.path.exists(sessions_dir):
        os.mkdir(sessions_dir)
    return sessions_dir


def getTestDbFile():
    if sys.platform in ('win32', 'win64'):
        return os.path.join(PACKAGEDIR, 'data/wtestdb')
    elif sys.platform == 'linux':
        return os.path.join(PACKAGEDIR, 'data/ltestdb')
    else:
        return '.'

def interface_coordpairs(coords, squarel):
    for k in range(len(coords) - 1):
        yield (np.array([[squarel / 2 + squarel * coords[k][1],
                          squarel / 2 + squarel * coords[k][0]],
                         [squarel / 2 + squarel * coords[k + 1][1],
                          squarel / 2 + squarel * coords[k + 1][0]]]))


def debug(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            logging.error(traceback.format_exc())
    return wrapper
