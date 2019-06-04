from ..core import *
from ..methods import *
from ..SchemeInput import createLocalData
import shelve

with shelve.open('/home/alpaca/aspy/db') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    linhas = np.array(linhas)[:, 0]
    trafos = np.array(trafos)[:, 0]

lt = LT(l=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2)
Y = np.array([[1/.12j, 0, -1/.12j], [0, 1/lt.Z + lt.Y/2, -1/lt.Z], [-1/.12j, -1/lt.Z, 1/.12j + 1/lt.Z + lt.Y/2]])
V0 = np.array([1.01, 1.02, 1.0], complex)
S = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])


def test_gauss_seidel():
    V = gauss_seidel(Y, V0, S, Niter=2)
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]), 0.77917)
    assert np.isclose(np.abs(V[2]), 0.997245)
    assert np.isclose(np.angle(V[2]), -0.0053719)


def test_gauss_seidel_eps():
    V = gauss_seidel(Y, V0, S, eps=1e-12)
    assert np.isclose(np.angle(V[1]), 0.83994)
    assert np.isclose(np.abs(V[2]), 0.996697)


def test_create_local_data():
    assert False, print(np.array([b.Z for b in barras]))


def test_Ybus():
    Ybarra = Ybus(barras, linhas, trafos, grid)
    assert np.all(np.isclose(Ybarra, Y))


def test_Yseq():
    Y0, Y1 = Yseq(barras, linhas, trafos, grid)
    assert False, print(np.linalg.inv(Y0))


def test_short():
    pass