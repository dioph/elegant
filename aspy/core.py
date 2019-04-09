import numpy as np
from scipy.stats.mstats import gmean


CORR = np.exp(-.25)
SQ2 = np.sqrt(2.)
OMEGA = 2 * np.pi * 60.
PI = np.pi
EPS = 8.854e-12


class Barra(object):
    def __init__(self, id=0, V=None, delta=None, pg=None, qg=None, pl=None, ql=None):
        self.id = id
        self.V = V
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.Vbase = None

    @property
    def P(self):
        return self.pg - self.pl

    @property
    def Q(self):
        return self.qg - self.ql


class BarraPQ(Barra):
    def __init__(self, id=0, pg=0., qg=0., pl=0., ql=0.):
        super(BarraPQ, self).__init__(id=id, V=np.nan, delta=np.nan, pg=pg, qg=qg, pl=pl, ql=ql)


class BarraPV(Barra):
    def __init__(self, id=0, V=1., pg=0., pl=0.):
        super(BarraPV, self).__init__(id=id, V=V, delta=np.nan, pg=pg, qg=np.nan, pl=pl, ql=np.nan)


class BarraSL(Barra):
    def __init__(self, id=0, V=1., delta=0.):
        super(BarraSL, self).__init__(id=id, V=V, delta=delta, pg=np.nan, qg=np.nan, pl=np.nan, ql=np.nan)


class LT(object):
    def __init__(self, l=80e3, r=2.5e-2, D=None, d=0.5, rho=1.78e-8, m=1):
        if D is None:
            D = [1.0, 1.0, 1.0]
        self.rho = rho
        self.l = l
        self.r = r
        self.D = np.atleast_1d(D)
        self.d = d
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
        R = self.rho * self.l / (self.m * PI * self.r**2)
        L = 2e-7 * np.log(gmean(self.D) / self.Rm) * self.l
        return R + OMEGA * L * 1j

    @property
    def Y(self):
        C = 2 * PI * EPS / np.log(gmean(self.D) / self.Rb) * self.l
        return OMEGA * C * 1j


class Trafo(object):
    def __init__(self, Snom=1e6, Vnom1=1e3, Vnom2=1e3, X=0.0):
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
