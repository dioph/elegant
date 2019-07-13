import shelve

from aspy.SchemeInput import createLocalData
from aspy.utils import getSessionsDir
from ..report import *

_SESSIONS_DIR_ = getSessionsDir()

with shelve.open(_SESSIONS_DIR_ + 'db') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    isolinhas = np.array(linhas)[:, 0]
    isotrafos = np.array(trafos)[:, 0]

def test_create_report():
    assert create_report(barras, isolinhas, isotrafos, grid)