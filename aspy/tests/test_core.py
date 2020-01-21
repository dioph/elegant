import unittest

from ..core import *


def ids_seq(system):
    buses = system.buses
    for i in range(len(buses) - 1):
        yield (buses[i].bus_id, buses[i + 1].bus_id)


def ids_slack(system):
    buses = system.buses.copy()
    _ = buses.pop(system.id2n(0))
    for i in range(len(buses)):
        yield (0, buses[i].bus_id)


def buses_ids(system):
    return [b.bus_id for b in system.buses]


class EightBusesCoreTests(unittest.TestCase):
    def setUp(self):
        self.system = PowerSystem()
        for i in range(8):
            self.system.add_bus()
        for ido, idd in ids_seq(self.system):
            self.system.add_line(TransmissionLine(orig=self.system.buses[ido], dest=self.system.buses[idd]))

    def test_TL_impedance(self):
        line = TransmissionLine(0, 0, z=1, y=1)
        self.assertEqual(line.Zpu, 1)
        self.assertEqual(line.Ypu, 1)

    def test_TL_parameters(self):
        line = TransmissionLine(0, 0)
        self.assertTrue(np.isclose(line.Zpu.real, .5666, atol=1e-4))
        self.assertTrue(np.isclose(line.Zpu.imag, 3.6607, atol=1e-4))
        self.assertTrue(np.isclose(line.Ypu.imag, 4.554e-5, atol=1e-4))

    def test_add_bus(self):
        curr_N = self.system.N
        self.system.add_bus()
        self.assertEqual(self.system.N, curr_N + 1)
        self.assertEqual(self.system.buses[0].bus_id, 0)
        self.assertEqual(self.system.buses[-1].bus_id, curr_N)

    def test_initial_setup(self):
        self.assertEqual(self.system.N, 8)
        self.assertEqual(self.system.M, 8)  # 8 interconnected buses
        self.assertEqual(self.system.buses[0].bus_id, 0)
        self.assertEqual(len(self.system.lines), 7)

    def test_slack_remove(self):
        self.system.remove_bus(self.system.id2n(0))
        self.assertFalse(0 in [b.bus_id for b in self.system.buses])
        self.assertTrue(buses_ids(self.system) == [i for i in range(1, 8)])

    def test_add_line_with_same_extremes(self):
        self.system.add_line(TransmissionLine(orig=self.system.buses[self.system.id2n(1)],
                                              dest=self.system.buses[self.system.id2n(1)]))
        self.assertEqual(len(self.system.lines), 7, 'the number of lines is {}'.format(len(self.system.lines)))

    def test_add_trafo_with_same_extremes(self):
        self.system.add_line(Transformer(orig=self.system.buses[self.system.id2n(1)],
                                         dest=self.system.buses[self.system.id2n(1)]))
        self.assertEqual(len(self.system.lines), 7, 'the number of lines is {}'.format(len(self.system.trafos)))

    def test_adding_lines_without_slack(self):
        self.system.remove_bus(self.system.id2n(0))  # lines 7 -> 6
        self.assertEqual(self.system.N, 7)
        for ido, idd in ids_seq(self.system):
            self.system.add_line(TransmissionLine(orig=self.system.buses[self.system.id2n(ido)],
                                                  dest=self.system.buses[self.system.id2n(idd)]))
        self.assertEqual(len(self.system.lines), 12)  # lines 6 -> 12
        self.system.add_bus()
        self.assertTrue(0 in buses_ids(self.system))  # slack added back
        for ido, idd in ids_slack(self.system):  # lines 12 -> 19
            self.system.add_line(TransmissionLine(orig=self.system.buses[self.system.id2n(ido)],
                                                  dest=self.system.buses[self.system.id2n(idd)]))
        self.assertEqual(len(self.system.lines), 19)
        self.system.remove_bus(self.system.id2n(0))  # lines 19 -> 12
        self.assertEqual(len(self.system.lines), 12)
        self.system.add_bus()
        self.assertTrue(0 in buses_ids(self.system))  # slack added back
        self.assertEqual(self.system.M, 1)
        self.assertEqual(self.system.N, 8)
        self.system.add_line(TransmissionLine(orig=self.system.buses[self.system.id2n(0)],
                                              dest=self.system.buses[self.system.id2n(1)]))  # lines 12 -> 13
        self.assertEqual(len(self.system.lines), 13)
        self.system.update(Nmax=1)

    def test_sort_buses(self):
        self.system.remove_bus(1)
        for i in range(self.system.N):
            self.assertEqual(i, self.system.buses[i].bus_id)
        self.system.remove_bus(0)
        self.assertEqual(1, self.system.buses[0].bus_id)

    def test_bus_load_connections_types(self):
        bus = Bus(bus_id=0)
        # Star
        self.assertEqual(1, bus.load_ground)
        # Grounded start
        bus.load_ground = STAR
        self.assertEqual(0, bus.load_ground)
        # Delta
        bus.load_ground = DELTA
        self.assertEqual(2, bus.load_ground)


class RealCasesCoreTests(unittest.TestCase):
    def setUp(self):
        self.system = PowerSystem()

    def test_remove_line(self):
        self.system.add_bus()
        self.system.add_bus()
        line = TransmissionLine(orig=self.system.buses[0], dest=self.system.buses[1])
        self.system.add_line(line)
        self.system.add_line(line)
        self.assertEqual(2, len(self.system.lines))
        self.system.remove_line(line)
        self.assertEqual(1, len(self.system.lines))
        self.assertEqual(2, self.system.M)
        self.assertEqual(2, self.system.N)

    def test_modifying_added_bus(self):
        bus = self.system.add_bus()
        self.system.buses[0].v = 10
        self.assertEqual(10, bus.v)

    def test_good_ids(self):
        self.system.add_bus()
        self.system.add_bus()
        self.system.add_bus()
        self.system.add_bus()
        for i, b in enumerate(self.system.buses):
            assert b.bus_id == i
        self.system.remove_bus(0)
        for i, b in enumerate(self.system.buses):
            assert b.bus_id == i + 1
        line = TransmissionLine(orig=self.system.buses[0], dest=self.system.buses[1])
        trafo = Transformer(orig=self.system.buses[0], dest=self.system.buses[1])
        self.system.add_line(line)  # bus 1 -> bus 2
        self.system.add_trafo(trafo)  # bus 1 -> bus 2
        assert self.system.M == 0
        self.system.add_bus()  # add slack
        assert self.system.M == 1
        line = TransmissionLine(orig=self.system.buses[0], dest=self.system.buses[1])
        self.system.add_line(line)  # slack <--> bus 1 <--> bus 2
        assert self.system.M == 3

    def test_3bus_problem_stevenson(self):
        slack = self.system.add_bus()
        pv = self.system.add_bus()
        pq = self.system.add_bus()
        bus_0 = self.system.buses[0]
        bus_1 = self.system.buses[1]
        bus_2 = self.system.buses[2]
        line = TransmissionLine(bus_2, bus_1, ell=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2)
        Y = np.array([[1 / .12j, 0, -1 / .12j],
                      [0, 1 / line.Zpu + line.Ypu / 2, -1 / line.Zpu],
                      [-1 / .12j, -1 / line.Zpu, 1 / .12j + 1 / line.Zpu + line.Ypu / 2]])
        self.system.add_line(line)
        trafo = Transformer(bus_0, bus_2, jx0=0.12, jx1=0.12, secondary=DELTA)
        self.system.add_trafo(trafo)
        self.assertTrue(np.allclose(self.system.Y, Y))
        slack.v = 1.01
        pv.pg = 0.08
        pv.v = 1.02
        pq.pl = 0.12
        pq.ql = 0.076
        self.system.update()
        self.assertTrue(np.isclose(pv.delta * 180 / np.pi, 48.125, atol=1e-5))


if __name__ == '__main__':
    unittest.main()
