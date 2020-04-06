import networkx as nx
import numpy as np
from scipy.stats.mstats import gmean

from .methods import newton_raphson, short

NAME = "Elegant"

CORR = np.exp(-.25)
SQ2 = np.sqrt(2.)
OMEGA = 2 * np.pi * 60.
PI = np.pi
EPS = 8.854e-12

STAR = 0
EARTH = 1
DELTA = 2
STAR_SYMBOL = "Y"
EARTH_SYMBOL = "Y\u23DA"
DELTA_SYMBOL = "\u0394"

PY_TO_SYMBOL = {STAR: STAR_SYMBOL, EARTH: EARTH_SYMBOL, DELTA: DELTA_SYMBOL}
SYMBOL_TO_PY = {STAR_SYMBOL: STAR, EARTH_SYMBOL: EARTH, DELTA_SYMBOL: DELTA}


# ToDo defasagem dos trafos

class Bus(object):
    """Generic bus class

    Attributes
    ----------
    bus_id: int
        Integer identifier
    v, delta: float, optional
        Complex voltage magnitude and phase (default=1.0)
    pg, qg: float, optional
        Generated active and reactive power (default=0.0)
    pl, ql: float, optional
        Load active and reactive power (default=0.0)
    xd: float, optional
        Subtransient reactance of the generator (default=`np.inf`)
    iTPG, iSLG, iDLGb, iDLGc, iLL: float or None
        Calculated short-circuit fault currents (default=None)
    gen_ground: bool, optional
        True if generator is grounded (default=False)
    load_ground: {STAR, EARTH, DELTA}
        Load connection type (default=EARTH)
    """
    def __init__(self, bus_id, v=1.0, delta=0.0, pg=0.0, qg=0.0, pl=0.0, ql=0.0,
                 xd=np.inf, iTPG=None, iSLG=None, iDLGb=None, iDLGc=None, iLL=None,
                 gen_ground=False, load_ground=EARTH):
        self.bus_id = bus_id
        self.v = v
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.xd = xd
        self.iTPG = iTPG
        self.iSLG = iSLG
        self.iDLGb = iDLGb
        self.iDLGc = iDLGc
        self.iLL = iLL
        self.gen_ground = gen_ground
        self.load_ground = load_ground

    @property
    def P(self):
        """
        Scheduled active power leaving the bus :math:`(P_{G,k}-P_{L,k})`
        """
        return self.pg - self.pl

    @property
    def Q(self):
        """
        Scheduled reactive power leaving the bus :math:`(Q_{G,k}-Q_{L,k})`
        """
        return self.qg - self.ql

    @property
    def Z(self):
        """
        Load impedance (constant)

        It is given by :math:`V_k^2/S_k^*` or `np.inf` if :math:`S_k=0`
        """
        if self.pl != 0 or self.ql != 0:
            return self.v ** 2 / (self.pl - 1j * self.ql)
        return np.inf


class TransmissionLine(object):
    """Transmission line class

    Attributes
    ----------
    orig, dest: Bus object
        Origin and destination buses
    ell: float, optional
        Line length in meters (default=10e3)
    r: float, optional
        Conductor radius in meters (default=1e-2)
    d12, d23, d31: float, optional
        Distances between each phase (default=1)
    d: float, optional
        Distances between conductors in each phase (default=0.5)
    rho: float, optional
        Conductor resistivity (default=1.78e-8)
    m: {1, 2, 3, 4}
        Number of conductors per phase (default=1)
    vbase: float, optional
        Voltage base (default=1e4)
    imax: float, optional
        Maximum supported ampacity (default=np.inf)
    z, y: float or None:
        Line distributed parameters (overwrites the line model)
    """
    def __init__(self, orig, dest, ell=10e3, r=1e-2, d12=1, d23=1, d31=1, d=0.5, rho=1.78e-8, m=1,
                 vbase=1e4, imax=np.inf, v1=0., v2=0., z=None, y=None):
        self.orig = orig
        self.dest = dest
        self.ell = ell
        self.r = r
        self.d12 = d12
        self.d23 = d23
        self.d31 = d31
        self.d = d
        self.rho = rho
        self.m = m
        self.z = z
        self.y = y
        self.vbase = vbase
        self.imax = imax
        self.v1 = v1
        self.v2 = v2

    @property
    def param(self):
        return dict(r=self.r,
                    d12=self.d12,
                    d23=self.d23,
                    d31=self.d31,
                    d=self.d,
                    rho=self.rho,
                    m=self.m,
                    imax=self.imax)

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
            R = self.rho * self.ell / (self.m * PI * self.r ** 2)
            L = 2e-7 * np.log(gmean([self.d12, self.d23, self.d31]) / self.Rm) * self.ell
            return R + OMEGA * L * 1j
        else:
            return self.z

    @property
    def Zpu(self):
        return self.Z / (self.vbase ** 2 / 1e8)

    @Z.setter
    def Z(self, z):
        self.z = z

    @property
    def Y(self):
        if (self.z, self.y) == (None, None):
            C = 2 * PI * EPS / np.log(gmean([self.d12, self.d23, self.d31]) / self.Rb) * self.ell
            return OMEGA * C * 1j
        else:
            return self.y

    @property
    def Ypu(self):
        return self.Y * (self.vbase ** 2 / 1e8)

    @Y.setter
    def Y(self, y):
        self.y = y

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
    def Ia(self):
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


class Transformer(object):
    def __init__(self, orig, dest, snom=1e8, jx0=0.5, jx1=0.5, primary=STAR, secondary=STAR, v1=0., v2=0.):
        self.orig = orig
        self.dest = dest
        self.snom = snom
        self.jx0 = jx0
        self.jx1 = jx1
        self.primary = primary
        self.secondary = secondary
        self.v1 = v1
        self.v2 = v2

    @property
    def Z0(self):
        return self.jx0 * 1e8j / self.snom

    @property
    def Z1(self):
        return self.jx1 * 1e8j / self.snom

    @property
    def Ipu(self):
        return (self.v1 - self.v2) / self.Z1

    @property
    def Sper(self):
        return self.Z1 * np.abs(self.Ipu) ** 2

    @property
    def S1(self):
        return self.S2 + self.Sper

    @property
    def S2(self):
        return self.v2 * self.Ipu.conjugate()


class Keys:
    def __init__(self):
        self.keys = {}

    def have_extremities(self, extremities):
        return extremities in self.keys.keys()

    def add_keyobj(self, extremities, path, obj):
        if self.have_extremities(extremities):
            self.keys[extremities][path] = obj
        else:
            self.keys[extremities] = {path: obj}

    def get_keyobj(self, extremities, path):
        return self.keys[extremities][path]


class PowerSystem(object):
    def __init__(self):
        self.buses = []
        self.lines = []
        self.trafos = []
        self.keys = Keys()
        self.graph = nx.MultiGraph()
        self.status = ""

    def add_bus(self):
        if 0 not in [bus.bus_id for bus in self.buses] or self.N == 0:
            bus = Bus(bus_id=0)
            self.buses.insert(0, bus)
        else:
            bus = Bus(bus_id=self.N + 1)
            self.buses.append(bus)
            self.status = "Inserted bus"
        self.sort_buses()
        self.graph.add_node(bus)
        return bus

    def add_line(self, line, path=None):
        if (line.orig, line.dest, path) in self.graph.edges:
            self.status = "key already exists!"
            return
        if line.orig == line.dest:
            self.status = "same origin and destiny buses not allowed"
            return
        self.lines.append(line)
        path = self.graph.add_edge(line.orig, line.dest, path)
        extremities = frozenset([line.orig, line.dest])
        self.keys.add_keyobj(extremities, path, line)

    def id2n(self, k):
        for n, bus in enumerate(self.buses):
            if bus.bus_id == k:
                return n

    def remove_bus(self, n):
        bus = self.buses[n]
        self.remove_elements_linked_to(bus)
        self.graph.remove_node(bus)
        self.buses.remove(bus)
        self.sort_buses()

    def add_trafo(self, trafo, path=None):
        if (trafo.orig, trafo.dest, path) in self.graph.edges:
            self.status = "key already exists!"
            return
        if trafo.orig == trafo.dest:
            self.status = "key already exists!"
            return
        self.trafos.append(trafo)
        path = self.graph.add_edge(trafo.orig, trafo.dest, path)
        extremities = frozenset([trafo.orig, trafo.dest])
        self.keys.add_keyobj(extremities, path, trafo)

    def remove_line(self, line, key=None):
        if key is not None and (line.orig, line.dest, key) not in self.graph.edges:
            self.status = "key does not exist!"
            return
        self.lines.remove(line)
        self.graph.remove_edge(line.orig, line.dest, key)
        self.status = "removed line"

    def remove_trafo(self, trafo, key=None):
        if key is not None and (trafo.orig, trafo.dest, key) not in self.graph.edges:
            self.status = "key does not exist!"
            return
        self.trafos.remove(trafo)
        self.graph.remove_edge(trafo.orig, trafo.dest, key)
        self.status = "removed transformer"

    def sort_buses(self):
        if 0 in [bus.bus_id for bus in self.buses]:
            for i in range(self.N):
                self.buses[i].bus_id = i
        else:
            for i in range(self.N):
                self.buses[i].bus_id = i + 1
        ids = [bus.bus_id for bus in self.buses]
        for line in self.lines:
            assert line.dest.bus_id in ids and line.orig.bus_id in ids
        for trafo in self.trafos:
            assert trafo.dest.bus_id in ids and trafo.orig.bus_id in ids

    def remove_elements_linked_to(self, bus):
        linked = []
        for edge in self.graph.edges:
            origin_bus, destiny_bus, path = edge
            if origin_bus == bus or destiny_bus == bus:
                extremities = frozenset([origin_bus, destiny_bus])
                obj = self.keys.get_keyobj(extremities, path)
                linked.append([obj, path])
        for obj, path in linked:
            if isinstance(obj, TransmissionLine):
                self.remove_line(obj, path)
            elif isinstance(obj, Transformer):
                self.remove_trafo(obj, path)

    @property
    def N(self):
        return len(self.buses)

    @property
    def M(self):
        buses = self.masked_buses
        return len(buses)

    @property
    def good_ids(self):
        buses = self.masked_buses
        good_ids = [bus.bus_id for bus in buses]
        return good_ids

    @property
    def hsh(self):
        good_ids = self.good_ids
        hsh = {}
        for j, i in enumerate(good_ids):
            hsh[i] = j
        return hsh

    @property
    def masked_buses(self):
        neighbors = []
        connected_components = nx.connected_components(self.graph)
        for component in connected_components:
            component_ids = [b.bus_id for b in component]
            if 0 in component_ids:  # and 0 in [b.bus_id for b in self.buses]
                neighbors = component_ids
        mask_buses = np.zeros(self.N, bool)
        if np.size(mask_buses):
            mask_buses[list(neighbors)] = True
        if self.N > 0:
            masked_buses = np.array(self.buses)[mask_buses]
        else:
            masked_buses = np.array([])
        return masked_buses

    @property
    def masked_lines(self):
        good_ids = self.good_ids
        mask_lines = np.ones(len(self.lines), bool)
        for i in range(len(self.lines)):
            line = self.lines[i]
            if line.orig.bus_id not in good_ids:
                mask_lines[i] = False
        if len(self.lines) > 0:
            masked_lines = np.array(self.lines)[mask_lines]
        else:
            masked_lines = np.array([])
        return masked_lines

    @property
    def masked_trafos(self):
        good_ids = self.good_ids
        mask_trafos = np.ones(len(self.trafos), bool)
        for i in range(len(self.trafos)):
            trafo = self.trafos[i]
            if trafo.orig.bus_id not in good_ids:
                mask_trafos[i] = False
        if len(self.trafos) > 0:
            masked_trafos = np.array(self.trafos)[mask_trafos]
        else:
            masked_trafos = np.array([])
        return masked_trafos

    @property
    def Y(self):
        N = self.M
        hsh = self.hsh
        lines = self.masked_lines
        trafos = self.masked_trafos
        Y = np.zeros((N, N), complex)
        for line in lines:
            node1 = hsh[line.orig.bus_id]
            node2 = hsh[line.dest.bus_id]
            Y[node1, node1] += 1 / line.Zpu + line.Ypu / 2
            Y[node2, node2] += 1 / line.Zpu + line.Ypu / 2
            Y[node1, node2] -= 1 / line.Zpu
            Y[node2, node1] -= 1 / line.Zpu
        for trafo in trafos:
            node1 = hsh[trafo.orig.bus_id]
            node2 = hsh[trafo.dest.bus_id]
            Y[node1, node1] += 1 / trafo.Z1
            Y[node2, node2] += 1 / trafo.Z1
            Y[node1, node2] -= 1 / trafo.Z1
            Y[node2, node1] -= 1 / trafo.Z1
        return Y

    @property
    def Y0(self):
        N = self.M
        hsh = self.hsh
        buses = self.masked_buses
        lines = self.masked_lines
        trafos = self.masked_trafos
        Y0 = np.zeros((N, N), complex)
        for bus in buses:
            node = hsh[bus.bus_id]
            if bus.gen_ground and np.isfinite(bus.xd):
                Y0[node, node] -= 1j / bus.xd
            if bus.load_ground == EARTH:
                Y0[node, node] += 1 / bus.Z
        for line in lines:
            node1 = hsh[line.orig.bus_id]
            node2 = hsh[line.dest.bus_id]
            Y0[node1, node1] += 1 / line.Zpu + line.Ypu / 2
            Y0[node2, node2] += 1 / line.Zpu + line.Ypu / 2
            Y0[node1, node2] -= 1 / line.Zpu
            Y0[node2, node1] -= 1 / line.Zpu
        for trafo in trafos:
            if trafo.primary == EARTH:
                if trafo.secondary == EARTH:
                    node1 = hsh[trafo.orig.bus_id]
                    node2 = hsh[trafo.dest.bus_id]
                    Y0[node1, node1] += 1 / trafo.Z0
                    Y0[node2, node2] += 1 / trafo.Z0
                    Y0[node1, node2] -= 1 / trafo.Z0
                    Y0[node2, node1] -= 1 / trafo.Z0
                elif trafo.secondary == DELTA:
                    node = hsh[trafo.orig.bus_id]
                    Y0[node, node] += 1 / trafo.Z0
            elif trafo.primary == DELTA and trafo.secondary == EARTH:
                node = hsh[trafo.dest.bus_id]
                Y0[node, node] += 1 / trafo.Z0
        return Y0

    @property
    def Y1(self):
        N = self.M
        hsh = self.hsh
        buses = self.masked_buses
        lines = self.masked_lines
        trafos = self.masked_trafos
        Y1 = np.zeros((N, N), complex)
        for bus in buses:
            node = hsh[bus.bus_id]
            Y1[node, node] += 1 / bus.Z
            if np.isfinite(bus.xd):
                Y1[node, node] -= 1j / bus.xd
        for line in lines:
            node1 = hsh[line.orig.bus_id]
            node2 = hsh[line.dest.bus_id]
            Y1[node1, node1] += 1 / line.Zpu + line.Ypu / 2
            Y1[node2, node2] += 1 / line.Zpu + line.Ypu / 2
            Y1[node1, node2] -= 1 / line.Zpu
            Y1[node2, node1] -= 1 / line.Zpu
        for trafo in trafos:
            node1 = hsh[trafo.orig.bus_id]
            node2 = hsh[trafo.dest.bus_id]
            Y1[node1, node1] += 1 / trafo.Z1
            Y1[node2, node2] += 1 / trafo.Z1
            Y1[node1, node2] -= 1 / trafo.Z1
            Y1[node2, node1] -= 1 / trafo.Z1
        return Y1

    def update(self, Nmax=100):
        buses = self.masked_buses
        lines = self.masked_lines
        trafos = self.masked_trafos
        hsh = self.hsh
        V, S = self.update_flow(Nmax=Nmax)
        for bus in buses:
            bus.v = np.abs(V[hsh[bus.bus_id]])
            bus.delta = np.angle(V[hsh[bus.bus_id]])
            bus.pg = np.round(S[hsh[bus.bus_id], 0], 4) + bus.pl
            bus.qg = np.round(S[hsh[bus.bus_id], 1], 4) + bus.ql
        for line in lines:
            node1 = hsh[line.orig.bus_id]
            node2 = hsh[line.dest.bus_id]
            line.v1 = V[node1]
            line.v2 = V[node2]
        for trafo in trafos:
            node1 = hsh[trafo.orig.bus_id]
            node2 = hsh[trafo.dest.bus_id]
            trafo.v1 = V[node1]
            trafo.v2 = V[node2]
        If = self.update_short()
        for bus in buses:
            bus.iTPG = If[hsh[bus.bus_id], 0, 0]
            bus.iSLG = If[hsh[bus.bus_id], 1, 0]
            bus.iDLGb = If[hsh[bus.bus_id], 2, 1]
            bus.iDLGc = If[hsh[bus.bus_id], 2, 2]
            bus.iLL = If[hsh[bus.bus_id], 3, 1]

    def update_flow(self, Nmax=100):
        N = self.M
        Y = self.Y
        buses = self.masked_buses
        V0 = np.zeros(N, complex)
        S0 = np.zeros((N, 2))
        for i in range(N):
            if buses[i].bus_id == 0:
                V0[i] = buses[i].v * np.exp(1j * buses[i].delta)
                S0[i] = np.array([np.nan, np.nan])
            elif buses[i].pg > 0:
                V0[i] = buses[i].v
                S0[i] = np.array([buses[i].pg - buses[i].pl, np.nan])
            else:
                V0[i] = 1.0
                S0[i] = np.array([-buses[i].pl, -buses[i].ql])
        niter, delta, V = newton_raphson(Y, V0, S0, eps=1e-12, Nmax=Nmax)
        Scalc = V * np.conjugate(np.dot(Y, V))
        S = np.zeros_like(S0)
        S[:, 0] = Scalc.real
        S[:, 1] = Scalc.imag
        if not np.allclose(S[np.isfinite(S0)], S0[np.isfinite(S0)]):
            self.status = "power mismatch!"
            return V0, S0
        return V, S

    def update_short(self):
        buses = self.masked_buses
        V = np.array([bus.v * np.exp(1j * bus.delta) for bus in buses])
        Y0 = self.Y0
        Y1 = self.Y1
        If = short(Y1, Y0, V)
        return If
