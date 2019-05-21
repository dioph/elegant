import numpy as np
from scipy.stats.mstats import gmean


CORR = np.exp(-.25)
SQ2 = np.sqrt(2.)
OMEGA = 2 * np.pi * 60.
PI = np.pi
EPS = 8.854e-12


class Barra(object):
    def __init__(self, barra_id=0, posicao=None, v=1.0, i=0.0, delta=0.0, pg=0.0, qg=0.0, pl=0.0, ql=0.0):
        self.barra_id = barra_id
        self.v = v
        self.i = i
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.vbase = 1e3
        self.posicao = posicao

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
    def __init__(self, l=80.0, r=1.0, d12=2.0, d23=2.0, d31=2.0, d=1.0, rho=1.78e-8, m=1.0, Z=None, Y=None, origin=None, destiny=None):
        self.rho = rho
        self.l = l
        self.r = r
        self.d12 = d12
        self.d23 = d23
        self.d31 = d31
        self.d = d
        self.m = m
        self.z = Z
        self.y = Y
        self.origin = origin
        self.destiny = destiny

    @property
    def Rm(self):
        if (self.z, self.y) == (None, None):
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
        if (self.z, self.y) == (None, None):
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
        if (self.z, self.y) == (None, None):
            R = self.rho * self.l / (self.m * PI * self.r**2)
            L = 2e-7 * np.log(gmean([self.d12, self.d23, self.d31]) / self.Rm) * self.l
            return R + OMEGA * L
        else:
            return self.z


    @Z.setter
    def Z(self, Z):
        self.z = Z


    @property
    def Y(self):
        if (self.z, self.y) == (None, None):
            C = 2 * PI * EPS / np.log(gmean([self.d12, self.d23, self.d31]) / self.Rb) * self.l
            return OMEGA * C * 1j
        else:
            return self.y


    @Y.setter
    def Y(self, Y):
        self.y = Y


class Trafo(object):
    def __init__(self, snom=1e6, vnom1=1e3, vnom2=1e3, jx0=0.0, jx1=0.0, connection='gYyg', origin=None, destiny=None):
        self.snom = snom
        self.vnom1 = vnom1
        self.vnom2 = vnom2
        self.jx0 = jx0
        self.jx1 = jx1
        self.connection = connection
        self.origin = origin
        self.destiny = destiny

    @property
    def Zbase1(self):
        return self.vnom1**2 / self.snom

    @property
    def Zbase2(self):
        return self.vnom2**2 / self.snom