import unittest

import numpy as np

from elegant.core import TransmissionLine
from elegant.methods import gauss_seidel, newton_raphson


class TestMethods(unittest.TestCase):
    def setUp(self):
        self.line = TransmissionLine(2, 1,
                                     ell=32e3, vbase=1e4,
                                     r=2.5e-2, d12=4.5, d23=3., d31=7.5, d=.4, m=2)
        lz = self.line.Zpu
        ly = self.line.Ypu
        self.Y = np.array([[1 / .12j, 0, -1 / .12j],
                           [0, 1 / lz + ly / 2, -1 / lz],
                           [-1 / .12j, -1 / lz, 1 / .12j + 1 / lz + ly / 2]])
        self.V0 = np.array([1.01, 1.02, 1.0], complex)
        self.S0 = np.array([[np.nan, np.nan], [0.08, np.nan], [-0.12, -0.076]])

    def test_gauss_seidel(self):
        niter, delta, v = gauss_seidel(self.Y, self.V0, self.S0, Niter=2)
        self.assertEqual(2, niter)
        self.assertAlmostEqual(1.01, v[0])
        self.assertAlmostEqual(1.02, np.abs(v[1]))
        self.assertAlmostEqual(44.643, np.rad2deg(np.angle(v[1])), places=3)
        self.assertAlmostEqual(0.99725, np.abs(v[2]), places=5)
        self.assertAlmostEqual(-0.3078, np.rad2deg(np.angle(v[2])), places=4)
        self.assertLess(1e-12, delta)

    def test_newton_raphson(self):
        niter, delta, v = newton_raphson(self.Y, self.V0, self.S0, Niter=2)
        self.assertEqual(2, niter)
        self.assertAlmostEqual(1.01, v[0])
        self.assertAlmostEqual(1.02, np.abs(v[1]))
        self.assertAlmostEqual(47.86, np.rad2deg(np.angle(v[1])), places=2)
        self.assertAlmostEqual(0.9968, np.abs(v[2]), places=4)
        self.assertAlmostEqual(-0.2804, np.rad2deg(np.angle(v[2])), places=5)
        self.assertLess(1e-12, delta)

    def test_scalc(self):
        niter, delta, v = newton_raphson(self.Y, self.V0, self.S0, Niter=2)
        s = v * np.conjugate(np.dot(self.Y, v))
        s_calc = np.empty_like(self.S0)
        s_calc[:, 0] = s.real
        s_calc[:, 1] = s.imag
        s_fixed = np.isfinite(self.S0)
        self.assertTrue(np.allclose(s_calc[s_fixed], self.S0[s_fixed], atol=1e-3))


if __name__ == '__main__':
    unittest.main()
