import shelve
from ..SchemeInput import createLocalData
from ..report import *


with shelve.open('C:\\Users\\Fernando Dantas\\Documents\\aspy\\db') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    isolinhas = np.array(linhas)[:, 0]
    isotrafos = np.array(trafos)[:, 0]


def test_create_report():
    assert create_report(barras, isolinhas, isotrafos, grid)