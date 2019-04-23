import numpy as np
from scipy.stats.mstats import gmean


CORR = np.exp(-.25)
SQ2 = np.sqrt(2.)
OMEGA = 2 * np.pi * 60.
PI = np.pi
EPS = 8.854e-12


class Barra(object):
    def __init__(self, barra_id=0, v=None, i=None, delta=None, pg=None, qg=None, pl=None, ql=None):
        self.barra_id = barra_id
        self.v = v
        self.i = i
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.vbase = 1e3

    @property
    def P(self):
        return self.pg - self.pl

    @property
    def Q(self):
        return self.qg - self.ql


class BarraPQ(Barra):
    def __init__(self, barra_id=0, pg=0., qg=0., pl=0., ql=0.):
        super(BarraPQ, self).__init__(barra_id=barra_id, v=np.nan, delta=np.nan, pg=pg, qg=qg, pl=pl, ql=ql)


class BarraPV(Barra):
    def __init__(self, barra_id=0, v=1e3, pg=0., pl=0., ql=0.):
        super(BarraPV, self).__init__(barra_id=barra_id, v=v, delta=np.nan, pg=pg, qg=np.nan, pl=pl, ql=ql)


class BarraSL(Barra):
    def __init__(self, barra_id=0, v=1e3, delta=0., pl=0., ql=0.):
        super(BarraSL, self).__init__(barra_id=barra_id, v=v, delta=delta, pg=np.nan, qg=np.nan, pl=pl, ql=ql)
        self.vbase = 1e3
        

class LT(object):
    def __init__(self, l=80e3, r=2.5e-2, d12=1.0, d23=1.0, d31=1.0, d=0.5, rho=1.78e-8, m=1):
        self.rho = rho
        self.l = l
        self.r = r
        self.d12 = d12
        self.d23 = d23
        self.d31 = d31
        self.d = d
        self.m = m
        self.vbase = 1e3

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
        L = 2e-7 * np.log(gmean([self.d12, self.d23, self.d31]) / self.Rm) * self.l
        return R + OMEGA * L * 1j

    @property
    def Y(self):
        C = 2 * PI * EPS / np.log(gmean([self.d12, self.d23, self.d31]) / self.Rb) * self.l
        return OMEGA * C * 1j


class Trafo(object):
    def __init__(self, snom=1e6, vnom1=1e3, vnom2=1e3, jx=0.0):
        self.snom = snom
        self.vnom1 = vnom1
        self.vnom2 = vnom2
        self.jx = jx

    @property
    def Zbase1(self):
        return self.vnom1**2 / self.snom

    @property
    def Zbase2(self):
        return self.vnom2**2 / self.snom
