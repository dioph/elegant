import logging
import os
import sys
import traceback

import numpy as np

from . import PACKAGEDIR


class LineSegment(object):
    def __init__(self, obj, coords, dlines, remove=False):
        self.coords = coords
        self.dlines = dlines
        self.obj = obj
        self.remove = remove


def getSessionsDir():
    if sys.platform in ('win32', 'win64'):
        home_dir = os.getenv('userprofile')
        sessions_dir = os.path.join(home_dir, 'Documents\\elegant')
    elif sys.platform == 'linux':
        home_dir = os.getenv('HOME')
        sessions_dir = os.path.join(home_dir, 'elegant')
    else:
        sessions_dir = '.'
    if not os.path.exists(sessions_dir):
        os.mkdir(sessions_dir)
    return sessions_dir


def getTestDbFile():
    return os.path.join(PACKAGEDIR, 'tests/testcase.pickle')


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


def safe_repr(val, unit=1.0, fmt="{:.3g}"):
    if val == np.inf:
        return "\u221E"
    return fmt.format(val / unit)


def safe_float(txt, unit=1.0):
    if txt == "\u221E":
        return np.inf
    try:
        val = float(txt) * unit
    except ValueError:
        val = np.nan
    return val
