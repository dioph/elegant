import shelve
from ..SchemeInput import createLocalData
from ..report import *
import numpy as np

with shelve.open('/home/alpaca/aspy/db') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    linhas = np.array(linhas)[:, 0]
    trafos = np.array(trafos)[:, 0]


def test_create_report():
    assert create_report(barras, linhas, trafos, grid)
