import numpy as np
from scipy.stats.mstats import gmean

CORR = np.exp(-.25)
SQ2 = np.sqrt(2.)
OMEGA = 2 * np.pi * 60.
PI = np.pi
EPS = 8.854e-12
N = 20

class Barra(object):
    def __init__(self, barra_id=0, posicao=None, v=1.0, i=0.0, delta=0.0, pg=0.0, qg=0.0, pl=0.0, ql=0.0,
                 xd=np.inf, iTPG=None, iSLG=None, iDLGb=None, iDLGc=None, iLL=None, rank=np.inf,
                 gen_ground=False, load_ground=True):
        self.barra_id = barra_id
        self.v = v
        self.i = i
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.posicao = posicao
        self.xd = xd
        self.iTPG = iTPG
        self.iSLG = iSLG
        self.iDLGb = iDLGb
        self.iDLGc = iDLGc
        self.iLL = iLL
        self.rank = rank
        self.gen_ground = gen_ground
        self.load_ground = load_ground

    @property
    def P(self):
        return self.pg - self.pl

    @property
    def Q(self):
        return self.qg - self.ql

    @property
    def Z(self):
        if self.pl != 0 or self.ql != 0:
            return self.v ** 2 / (self.pl - 1j * self.ql)
        return np.inf


class LT(object):
    def __init__(self, l=32e3, r=2.5e-2, d12=3.0, d23=4.5, d31=7.5, d=0.4, rho=1.78e-8, m=2, vbase=1e4,
                 imax=np.inf, v1=0., v2=0., Z=None, Y=None, origin=None, destiny=None):
        self.rho = rho
        self.r = r
        self.d12 = d12
        self.d23 = d23
        self.d31 = d31
        self.d = d
        self.m = m
        if imax is None:
            imax = np.inf
        self.imax = imax
        self.l = l
        self.z = Z
        self.y = Y
        self.origin = origin
        self.destiny = destiny
        self.vbase = vbase
        self.v1 = v1
        self.v2 = v2

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
            R = self.rho * self.l / (self.m * PI * self.r ** 2)
            L = 2e-7 * np.log(gmean([self.d12, self.d23, self.d31]) / self.Rm) * self.l
            return R + OMEGA * L * 1j
        else:
            return self.z

    @property
    def Zpu(self):
        return self.Z / (self.vbase ** 2 / 1e8)

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

    @property
    def Ypu(self):
        return self.Y * (self.vbase ** 2 / 1e8)

    @Y.setter
    def Y(self, Y):
        self.y = Y

    @property
    def gamma(self):
        return np.sqrt(self.Z * self.Y)

    @property
    def Zc(self):
        return np.sqrt(self.Z / self.Y)

    @property
    def Zcpu(self):
        return np.sqrt(self.Zpu / self.Ypu)

    @property
    def Tpu(self):
        A = (self.Zpu * self.Ypu / 2 + 1)
        B = self.Zpu
        C = self.Ypu * (1 + self.Zpu * self.Ypu / 4)
        return np.array([[A, B], [C, A]])

    @property
    def Ipu(self):
        A, B, C, D = self.Tpu.flatten()
        return (self.v1 - A * self.v2) / B

    @property
    def I(self):
        ibase = 1e8 / self.vbase
        return self.Ipu * ibase

    @property
    def Sper(self):
        return self.S1 - self.S2

    @property
    def S1(self):
        v1 = np.abs(self.v1)
        v2 = np.abs(self.v2)
        d12 = np.angle(self.v1) - np.angle(self.v2)
        z = np.abs(self.Zpu)
        dz = np.angle(self.Zpu)
        P1 = v1 ** 2 / z * np.cos(dz) - v1 * v2 / z * np.cos(d12 + dz)
        Q1 = v1 ** 2 / z * np.sin(dz) - v1 * v2 / z * np.sin(d12 + dz) - v1 ** 2 * np.abs(self.Ypu) / 2
        return P1 + 1j * Q1

    @property
    def S2(self):
        v1 = np.abs(self.v1)
        v2 = np.abs(self.v2)
        d12 = np.angle(self.v1) - np.angle(self.v2)
        z = np.abs(self.Zpu)
        dz = np.angle(self.Zpu)
        P2 = -v2 ** 2 / z * np.cos(dz) + v1 * v2 / z * np.cos(-d12 + dz)
        Q2 = -v2 ** 2 / z * np.sin(dz) + v1 * v2 / z * np.sin(-d12 + dz) + v2 ** 2 * np.abs(self.Ypu) / 2
        return P2 + 1j * Q2


class Trafo(object):
    def __init__(self, snom=1e8, jx0=0.5, jx1=0.5, primary=0, secondary=0, origin=None, destiny=None, v1=0., v2=0.):
        self.snom = snom
        self.jx0 = jx0
        self.jx1 = jx1
        self.primary = primary
        self.secondary = secondary
        self.origin = origin
        self.destiny = destiny
        self.v1 = v1
        self.v2 = v2

    @property
    def Z0(self):
        return self.jx0 * 1e8 * 1j / self.snom

    @property
    def Z1(self):
        return self.jx1 * 1e8 * 1j / self.snom

    @property
    def Ipu(self):
        return (self.v1 - self.v2) / self.Z1

    @property
    def Sper(self):
        return self.Z1 * np.abs(self.Ipu) ** 2

    @property
    def Spu(self):
        return self.v2 * self.Ipu.conjugate()
