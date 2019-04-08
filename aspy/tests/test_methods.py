from ..core import *
from ..methods import *


def test_gauss_seidel():
    lt = LT(l=32e3, r=2.5e-2, D=[4.5, 3.0, 7.5], d=0.4, m=2)
    Y = np.array([[1/.12j, 0, -1/.12j], [0, 1/lt.Z, -1/lt.Z], [-1/.12j, -1/lt.Z, 1/.12j + 1/lt.Z]])
    V0 = np.array([1.01, 1.02, 1.0], complex)
    S = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])
    V = gauss_seidel(Y, V0, S, Niter=2)
    assert V[0] == 1.01
    assert np.abs(V[1]) == 1.02
    assert 0.7789 < np.angle(V[1]) < 0.7790      # 0.7789653586984024
    assert 0.9972 < np.abs(V[2]) < 0.9973        # 0.9972446877630761
    assert -0.00538 < np.angle(V[2]) < -0.00537  # -0.005373827344609707


def test_gauss_seidel_eps():
    lt = LT(l=32e3, r=2.5e-2, D=[4.5, 3.0, 7.5], d=0.4, m=2)
    Y = np.array([[1 / .12j, 0, -1 / .12j], [0, 1 / lt.Z, -1 / lt.Z], [-1 / .12j, -1 / lt.Z, 1 / .12j + 1 / lt.Z]])
    V0 = np.array([1.01, 1.02, 1.0], complex)
    S = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])
    V = gauss_seidel(Y, V0, S, eps=1e-12)
    assert 0.83995 < np.angle(V[1]) < 0.83996    # 0.8399539878857528
    assert 0.99668 < np.abs(V[2]) < 0.99669      # 0.9966868043172695


def test_newton_raphson():
    Y = np.array([
        [8.985190 - 44.835953 * 1j, -3.815629 + 19.078144 * 1j, -5.169561 + 25.847809 * 1j, 0],
        [-3.815629 + 19.078144 * 1j, 8.985190 - 44.835953 * 1j, 0, -5.169561 + 25.847809 * 1j],
        [-5.169561 + 25.847809 * 1j, 0, 8.193267 - 40.863838 * 1j, -3.023705 + 15.118528 * 1j],
        [0, -5.169561 + 25.847809 * 1j, -3.023705 + 15.118528 * 1j, 8.193267 - 40.863838 * 1j]
    ])

    V0 = np.array([1.0, 1.0, 1.0, 1.02], complex)
    S = np.array([[np.nan, np.nan], [-1.7, -1.0535], [-2, -1.2394], [2.38, np.nan]])
    V = newton_raphson(Y, V0, S, eps=1e-12)
    print(V)
    assert V[0] == 1.0
    assert np.abs(np.abs(V[3])-1.02) < 1e-6
    assert 0.98227 < np.real(V[1]) < 0.98228
