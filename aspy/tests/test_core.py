from ..core import *


def test_TL_impedance():
    line = TL(0, 0, z=1, y=1)
    assert line.Zpu == 1
    assert line.Ypu == 1


def test_TL_parameters():
    line = TL(0, 0)
    assert np.isclose(line.Zpu.real, .5666, atol=1e-4)
    assert np.isclose(line.Zpu.imag, 3.6607, atol=1e-4)
    assert np.isclose(line.Ypu.imag, 4.554e-5)


def test_add_bus():
    system = PowerSystem()
    system.add_bus()
    assert system.N == 1
    assert system.buses[0].bus_id == 0


def test_sort_buses():
    system = PowerSystem()
    system.add_bus()
    system.add_bus()
    system.add_bus()
    # [0, 1, 2]
    system.remove_bus(1)
    # [0, 2] --> [0, 1]
    for i in range(system.N):
        assert system.buses[i].bus_id == i
    system.remove_bus(0)
    # [1] --> [1]
    assert system.buses[0].bus_id == 1


def test_remove_line():
    system = PowerSystem()
    system.add_bus()
    system.add_bus()
    line = TL(orig=0, dest=1)
    system.add_line(line)
    system.add_line(line)
    assert len(system.lines) == 2
    system.remove_line(line)
    assert len(system.lines) == 1
    assert system.M == system.N == 2


def test_modifying_added_bus():
    system = PowerSystem()
    bus = system.add_bus()
    system.buses[0].v = 10
    assert bus.v == 10


def test_3bus_problem_stevenson():
    system = PowerSystem()
    slack = system.add_bus()
    pv = system.add_bus()
    pq = system.add_bus()
    line = TL(2, 1, ell=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2)
    Y = np.array([[1 / .12j, 0, -1 / .12j],
                  [0, 1 / line.Zpu + line.Ypu / 2, -1 / line.Zpu],
                  [-1 / .12j, -1 / line.Zpu, 1 / .12j + 1 / line.Zpu + line.Ypu / 2]])
    system.add_line(line)
    xfmr = Transformer(0, 2, jx0=0.12, jx1=0.12, secondary=DELTA)
    system.add_xfmr(xfmr)
    assert np.allclose(system.Y, Y)
    slack.v = 1.01
    pv.pg = 0.08
    pv.v = 1.02
    pq.pl = 0.12
    pq.ql = 0.076
    system.update()
    assert np.isclose(pv.delta * 180 / np.pi, 48.125, atol=1e-5)
