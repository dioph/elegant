from aspy.interface import *
from aspy.report import *

with shelve.open(os.path.join(PACKAGEDIR, './data/testdb')) as db:
    system = db['SYSTEM']
    curves = db['CURVES']

SESSIONS_DIR = getSessionsDir()


def test_create_report():
    assert create_report(system, curves, os.path.join(SESSIONS_DIR, 'test.pdf'))
