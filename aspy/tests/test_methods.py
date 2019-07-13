import shelve

from aspy.SchemeInput import createLocalData
from ..core import *
from ..methods import *

with shelve.open('aspy/data/testdb') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    linhas = np.array(linhas)[:, 0]
    trafos = np.array(trafos)[:, 0]


def setup():
    global lt, Y, V0, S
    lt = LT(l=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2, vbase=1.0e4)
    Y = np.array([[1 / .12j, 0, -1 / .12j], [0, 1 / lt.Zpu + lt.Ypu / 2, -1 / lt.Zpu],
                  [-1 / .12j, -1 / lt.Zpu, 1 / .12j + 1 / lt.Zpu + lt.Ypu / 2]])
    V0 = np.array([1.01, 1.02, 1.0], complex)
    S = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])


def test_gauss_seidel():
    setup()
    niter, delta, V = gauss_seidel(Y, V0, S, Niter=2)
    assert niter == 2
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 44.643)
    assert np.isclose(np.abs(V[2]), 0.99725)
    assert np.isclose(np.angle(V[2]) * 180 / np.pi, -0.3078, atol=1e-5)


def test_gauss_seidel_eps():
    setup()
    niter, delta, V = gauss_seidel(Y, V0, S, eps=1e-12)
    assert delta < 1e-12
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 48.125, atol=1e-5)
    assert np.isclose(np.abs(V[2]), 0.9967)


def test_newton_raphson():
    setup()
    niter, delta, V = newton_raphson(Y, V0, S, Niter=2)
    assert niter == 2
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 47.86)
    assert np.isclose(np.abs(V[2]), 0.9968)
    assert np.isclose(np.angle(V[2]) * 180 / np.pi, -0.2804, atol=1e-5)


def test_newton_raphson_eps():
    setup()
    niter, delta, V = newton_raphson(Y, V0, S, eps=1e-12)
    assert delta < 1e-12
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 48.125, atol=1e-5)
    assert np.isclose(np.abs(V[2]), 0.9967)


def test_Ybus():
    Ybarra = Ybus(barras, linhas, trafos, grid)
    assert np.allclose(Ybarra, Y)


def test_Scalc():
    niter, err, V = newton_raphson(Y, V0, S, eps=1e-12)
    I = np.dot(Y, V)
    Scalc = V * np.conjugate(I)
    S0 = np.zeros_like(S)
    S0[:, 0] = Scalc.real
    S0[:, 1] = Scalc.imag
    assert np.allclose(S0[np.isfinite(S)], S[np.isfinite(S)])


def test_short():
    setup()
    Y0, Y1 = Yseq(barras, linhas, trafos, grid)
    niter, err, V = newton_raphson(Y, V0, S, eps=1e-12)
    I = short(Y1, Y0, V)
    assert I.shape == (3, 4, 3)
    # TPG is symmetric
    assert np.allclose(np.abs(I[0, 0, :]), np.abs(I[0, 0, 0]))
    # SLG has no iB (nor iC) current
    assert np.allclose(np.abs(I[:, 1, 1]), 0.0)
    # LL iB + iC == 0
    assert np.allclose(I[:, 3, 1], -I[:, 3, 2])
