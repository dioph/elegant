from aspy.interface import *
from aspy.report import *

with open(os.path.join(PACKAGEDIR, './data/testdb'), 'br') as file:
    db = pickle.load(file)
    system = db['SYSTEM']
    curves = db['CURVES']
    grid = db['GRID']

SESSIONS_DIR = getSessionsDir()


def test_create_report():
    assert create_report(system, curves, grid, os.path.join(SESSIONS_DIR, 'test.pdf'))
