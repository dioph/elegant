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

