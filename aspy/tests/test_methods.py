import shelve

from ..SchemeInput import createLocalData
from ..core import *
from ..methods import *


with shelve.open('C:\\Users\\Fernando Dantas\\Documents\\GitHub\\aspy\\test\\test_file') as db:
    tipos, linhas, barras, trafos, grid = createLocalData(db)
    linhas = np.array(linhas)[:, 0]
    trafos = np.array(trafos)[:, 0]


def setup():
    global lt, Y, V0, S
    lt = LT(l=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2, vbase=1.0e4)
    Y = np.array([[1/.12j, 0, -1/.12j], [0, 1/lt.Zpu + lt.Ypu/2, -1/lt.Zpu], [-1/.12j, -1/lt.Zpu, 1/.12j + 1/lt.Zpu + lt.Ypu/2]])
    V0 = np.array([1.01, 1.02, 1.0], complex)
    S = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])


def test_gauss_seidel():
    setup()
    niter, delta, V = gauss_seidel(Y, V0, S, Niter=2)
    assert niter == 2
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]), 0.779175)
    assert np.isclose(np.abs(V[2]), 0.997253)
    assert np.isclose(np.angle(V[2]), -0.005371912)


def test_gauss_seidel_eps():
    setup()
    niter, delta, V = gauss_seidel(Y, V0, S, eps=1e-12)
    assert delta < 1e-12
    assert np.isclose(np.angle(V[1]), 0.83994)
    assert np.isclose(np.abs(V[2]), 0.996697)


def test_newton_raphson():
    setup()
    niter, delta, V = newton_raphson(Y, V0, S, Niter=2)
    assert niter == 2
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]), 0.835314)
    assert np.isclose(np.abs(V[2]), 0.9968)
    assert np.isclose(np.angle(V[2]), -0.00489395)


def test_newton_raphson_eps():
    setup()
    niter, delta, V = newton_raphson(Y, V0, S, eps=1e-12)
    assert delta < 1e-12
    assert np.isclose(np.angle(V[1]), 0.83994)
    assert np.isclose(np.abs(V[2]), 0.996697)


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
    # DLG iB == iC
    assert np.allclose(I[:, 2, 1], I[:, 2, 2])
    # LL iB + iC == 0
    assert np.allclose(I[:, 3, 1], -I[:, 3, 2])


def test_plot():
    setup()
    N = len(barras)
    V1 = np.zeros(N, complex)
    S0 = np.zeros((N, 2))
    for i in range(N):
        if barras[i].pg > 0 and barras[i].barra_id > 0:
            V1[i] = barras[i].v
            S0[i] = np.array([barras[i].pg - barras[i].pl, np.nan])
        elif barras[i].barra_id == 0:
            V1[i] = barras[i].v * np.exp(barras[i].delta * 1j)
            S0[i] = np.array([np.nan, np.nan])
        else:
            V1[i] = 1.0
            S0[i] = np.array([-barras[i].pl, -barras[i].ql])
    assert np.allclose(V1, V0)
    Ybarra = Ybus(barras, linhas, trafos, grid)
    niter, delta, V = newton_raphson(Ybarra, V1, S0, eps=1e-6)
    ax = plt.subplot(111, projection='polar')
    ax.set_rlim(.5, 1.2)
    ax.set_thetalim(-1, 1)
    ax.plot(np.angle(V), np.abs(V), 'ko')
    plt.show()

