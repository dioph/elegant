import shelve

from aspy.utils import createLocalData, getSessionsDir
from ..report import *

_SESSIONS_DIR_ = getSessionsDir()

with shelve.open(_SESSIONS_DIR_ + 'db') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    isolinhas = np.array(linhas)[:, 0]
    isotrafos = np.array(trafos)[:, 0]

def test_create_report():
    assert create_report(barras, isolinhas, isotrafos, grid)