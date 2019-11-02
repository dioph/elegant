from ..core import *
from ..methods import *


def setup():
    line = TL(2, 1, ell=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2, vbase=1.0e4)
    Y = np.array([[1 / .12j, 0, -1 / .12j],
                  [0, 1 / line.Zpu + line.Ypu / 2, -1 / line.Zpu],
                  [-1 / .12j, -1 / line.Zpu, 1 / .12j + 1 / line.Zpu + line.Ypu / 2]])
    V0 = np.array([1.01, 1.02, 1.0], complex)
    S0 = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])
    return line, Y, V0, S0


def test_gauss_seidel():
    line, Y, V0, S0 = setup()
    niter, delta, V = gauss_seidel(Y, V0, S0, Niter=2)
    assert niter == 2
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 44.643)
    assert np.isclose(np.abs(V[2]), 0.99725)
    assert np.isclose(np.angle(V[2]) * 180 / np.pi, -0.3078, atol=1e-5)


def test_gauss_seidel_eps():
    line, Y, V0, S0 = setup()
    niter, delta, V = gauss_seidel(Y, V0, S0, eps=1e-12)
    assert delta < 1e-12
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 48.125, atol=1e-5)
    assert np.isclose(np.abs(V[2]), 0.9967)


def test_newton_raphson():
    line, Y, V0, S0 = setup()
    niter, delta, V = newton_raphson(Y, V0, S0, Niter=2)
    assert niter == 2
    assert np.isclose(V[0], 1.01)
    assert np.isclose(np.abs(V[1]), 1.02)
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 47.86)
    assert np.isclose(np.abs(V[2]), 0.9968)
    assert np.isclose(np.angle(V[2]) * 180 / np.pi, -0.2804, atol=1e-5)


def test_newton_raphson_eps():
    line, Y, V0, S0 = setup()
    niter, delta, V = newton_raphson(Y, V0, S0, eps=1e-12)
    assert delta < 1e-12
    assert np.isclose(np.angle(V[1]) * 180 / np.pi, 48.125, atol=1e-5)
    assert np.isclose(np.abs(V[2]), 0.9967)


def test_Scalc():
    line, Y, V0, S0 = setup()
    niter, err, V = newton_raphson(Y, V0, S0, eps=1e-12)
    Scalc = V * np.conjugate(np.dot(Y, V))
    S = np.zeros_like(S0)
    S[:, 0] = Scalc.real
    S[:, 1] = Scalc.imag
    assert np.allclose(S[np.isfinite(S0)], S0[np.isfinite(S0)])
