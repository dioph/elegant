import logging
import os
import sys
import traceback

from PyQt5.QtCore import QObject, pyqtSignal


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


def debug(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            logging.error(traceback.format_exc())
    return wrapper
