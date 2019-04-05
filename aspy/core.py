from _methods import GaussSeidel
import numpy as np
from scipy.stats.mstats import gmean


CORR = np.exp(-.25)
SQ2 = np.sqrt(2.)
OMEGA = 2 * np.pi * 60.
PI = np.pi
EPS = 8.854e-12


class Barra(object):
    def __init__(self, v=None, delta=None, pg=None, qg=None, pl=None, ql=None):
        self.v = v
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql


class LT(object):
    def __init__(self, l, r, D, d, rho=1.78e-8, n=3, m=1):
        self.rho = rho
        self.l = l
        self.r = r
        self.D = np.atleast_1d(D)
        self.d = d
        self.n = n
        self.m = m

    @property
    def Rm(self):
        if self.m == 1:
            return CORR * self.r
        elif self.m == 2:
            return gmean([CORR * self.r, self.d])
        elif self.m == 3:
            return gmean([CORR * self.r, self.d, self.d])
        elif self.m == 4:
            return gmean([CORR * self.r, self.d, self.d, SQ2 * self.d])
        else:
            return np.nan

    @property
    def Rb(self):
        if self.m == 1:
            return self.r
        elif self.m == 2:
            return gmean([self.r, self.d])
        elif self.m == 3:
            return gmean([self.r, self.d, self.d])
        elif self.m == 4:
            return gmean([self.r, self.d, self.d, SQ2 * self.d])
        else:
            return np.nan

    @property
    def Z(self):
        R = self.rho * self.l / (self.m * np.pi * self.r**2)
        L = 2e-7 * np.log(gmean(self.D) / self.Rm) * self.l
        return R + OMEGA * L * 1j

    @property
    def Y(self):
        C = 2 * PI * EPS / np.log(gmean(self.D) / self.Rb) * self.l
        return OMEGA * C * 1j


class Trafo(object):
    def __init__(self, Snom, Vnom1, Vnom2, X):
        self.Snom = Snom
        self.Vnom1 = Vnom1
        self.Vnom2 = Vnom2
        self.X = X

    @property
    def Zbase1(self):
        return self.Vnom1**2 / self.Snom

    @property
    def Zbase2(self):
        return self.Vnom2**2 / self.Snom