import logging
import os
import sys
import traceback

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

N = 20

class GenericSignal(QObject):
    signal = pyqtSignal(object)

    def __init__(self):
        super(GenericSignal, self).__init__()

    def emit_sig(self, args):
        self.signal.emit(args)


def reset_system_state_variables():
    global BUSES, LINES, TRANSFORMERS, GRID_BUSES, BUSES_PIXMAP
    LINES, BUSES, TRANSFORMERS = [], [], []
    GRID_BUSES = np.zeros((N, N), object)
    BUSES_PIXMAP = np.zeros((N, N), object)


def storeData(db):
    global LINES, BUSES, TRANSFORMERS, LINE_TYPES, GRID_BUSES
    filtered_lines = []
    for line in LINES:
        filtered_lines.append([line[0], [], line[2], False])
    db['LINES'] = filtered_lines
    db['BUSES'] = BUSES
    db['GRID_BUSES'] = GRID_BUSES
    filtered_trafos = []
    for trafo in TRANSFORMERS:
        filtered_trafos.append([trafo[0], [], trafo[2], False])  # aspy.core.Trafo/coordinates
    db['TRANSFORMERS'] = filtered_trafos
    db['LINE_TYPES'] = LINE_TYPES
    return db


def createLocalData(db):
    global LINES, BUSES, TRANSFORMERS, LINE_TYPES, GRID_BUSES
    LINE_TYPES = db['LINE_TYPES']
    LINES = db['LINES']
    BUSES = db['BUSES']
    TRANSFORMERS = db['TRANSFORMERS']
    GRID_BUSES = db['GRID_BUSES']
    return LINE_TYPES, LINES, BUSES, TRANSFORMERS, GRID_BUSES


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


def debug(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            logging.error(traceback.format_exc())
    return wrapper
