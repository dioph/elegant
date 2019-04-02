class Barra(object):
    def __init__(self, v=None, delta=None, pg=None, qg=None, pl=None, ql=None):
        self.v = v
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql


class LT(object):
    def __init__(self, l, D, d, n=3, m=1):
        self.l = l
        self.D = D
        self.d = d
        self.n = n
        self.m = m

    def ckt(self):
        if self.l <= 80e3:
            pass
        elif self.l <= 240e3:
            pass
        else:
            pass

