from ..core import *
from ..methods import *
import unittest


class TestMethods(unittest.TestCase):
    def setUp(self):
        self.line = TransmissionLine(2, 1, ell=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2, vbase=1.0e4)
        self.Y = np.array([[1 / .12j, 0, -1 / .12j],
                           [0, 1 / self.line.Zpu + self.line.Ypu / 2, -1 / self.line.Zpu],
                           [-1 / .12j, -1 / self.line.Zpu, 1 / .12j + 1 / self.line.Zpu + self.line.Ypu / 2]])
        self.V0 = np.array([1.01, 1.02, 1.0], complex)
        self.S0 = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])

    def test_gauss_seidel(self):
        niter, delta, V = gauss_seidel(self.Y, self.V0, self.S0, Niter=2)
        self.assertEqual(2, niter)
        self.assertAlmostEqual(1.01, V[0])
        self.assertAlmostEqual(1.02, np.abs(V[1]))
        self.assertAlmostEqual(44.643, np.rad2deg(np.angle(V[1])), places=3)
        self.assertAlmostEqual(0.99725, np.abs(V[2]), places=5)
        self.assertAlmostEqual(-0.3078, np.rad2deg(np.angle(V[2])), places=4)
        self.assertLess(1e-12, delta)

    def test_newton_raphson(self):
        niter, delta, V = newton_raphson(self.Y, self.V0, self.S0, Niter=2)
        self.assertEqual(2, niter)
        self.assertAlmostEqual(1.01, V[0])
        self.assertAlmostEqual(1.02, np.abs(V[1]))
        self.assertAlmostEqual(47.86, np.rad2deg(np.angle(V[1])), places=2)
        self.assertAlmostEqual(0.9968, np.abs(V[2]), places=4)
        self.assertAlmostEqual(-0.2804, np.rad2deg(np.angle(V[2])), places=5)
        self.assertLess(1e-12, delta)

    def test_scalc(self):
        niter, delta, V = newton_raphson(self.Y, self.V0, self.S0, Niter=2)
        Scalc = V * np.conjugate(np.dot(self.Y, V))
        S = np.zeros_like(self.S0)
        S[:, 0] = Scalc.real
        S[:, 1] = Scalc.imag
        self.assertTrue(np.allclose(S[np.isfinite(self.S0)], self.S0[np.isfinite(self.S0)], atol=1e-3))


if __name__ == '__main__':
    unittest.main()
