import unittest
from aspy.core import *


def ids_seq(system):
    buses = system.buses
    for i in range(len(buses) - 1):
        yield (buses[i].bus_id, buses[i+1].bus_id)


def ids_slack(system):
    buses = system.buses.copy()
    _ = buses.pop(system.id2n(0))
    for i in range(len(buses)):
        yield (0, buses[i].bus_id)


def buses_ids(system):
    return [b.bus_id for b in system.buses]


class Bug(unittest.TestCase):
    def setUp(self):
        self.system = PowerSystem()
        for i in range(8):
            self.system.add_bus()
        for ido, idd in ids_seq(self.system):
            self.system.add_line(TL(orig=self.system.buses[ido], dest=self.system.buses[idd]))

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
        self.system.add_line(TL(orig=self.system.buses[self.system.id2n(1)],
                                    dest=self.system.buses[self.system.id2n(1)]))
        self.assertEqual(len(self.system.lines), 7, 'the number of lines is {}'.format(len(self.system.lines)))

    def test_add_xfmr_with_same_extremes(self):
        self.system.add_line(Transformer(orig=self.system.buses[self.system.id2n(1)],
                                    dest=self.system.buses[self.system.id2n(1)]))
        self.assertEqual(len(self.system.lines), 7, 'the number of lines is {}'.format(len(self.system.xfmrs)))

    def test_adding_lines_without_slack(self):
        self.system.remove_bus(self.system.id2n(0))  # lines 7 -> 6
        self.assertEqual(self.system.N, 7)
        for ido, idd in ids_seq(self.system):
            self.system.add_line(TL(orig=self.system.buses[self.system.id2n(ido)],
                                    dest=self.system.buses[self.system.id2n(idd)]))
        self.assertEqual(len(self.system.lines), 12)  # lines 6 -> 12
        self.system.add_bus()
        self.assertTrue(0 in buses_ids(self.system))  # slack added back
        for ido, idd in ids_slack(self.system):  # lines 12 -> 19
            self.system.add_line(TL(orig=self.system.buses[self.system.id2n(ido)],
                                    dest=self.system.buses[self.system.id2n(idd)]))
        self.assertEqual(len(self.system.lines), 19)
        self.system.remove_bus(self.system.id2n(0))  # lines 19 -> 12
        self.assertEqual(len(self.system.lines), 12)
        self.system.add_bus()
        self.assertTrue(0 in buses_ids(self.system))  # slack added back
        self.assertEqual(self.system.M, 1)
        self.assertEqual(self.system.N, 8)
        self.system.add_line(TL(orig=self.system.buses[self.system.id2n(0)],
                                dest=self.system.buses[self.system.id2n(1)]))  # lines 12 -> 13
        self.assertEqual(len(self.system.lines), 13)
        self.system.update(Nmax=1)

if __name__ == '__main__':
    unittest.main()
