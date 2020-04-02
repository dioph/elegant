import unittest

from PyQt5.QtWidgets import *

from elegant.interface import Software
from ..utils import *

from ..core import STAR, EARTH, DELTA, STAR_SYMBOL, EARTH_SYMBOL, DELTA_SYMBOL


class ElegantQt(QWidget):
    def __init__(self, *args, **kwargs):
        super(ElegantQt, self).__init__(*args, *kwargs)
        self.software = Software()
        self.software.initUI()

    def insertion_mode(self):
        self.software.circuit.InsertionModeRadioButton.setChecked(True)

    def real_time_mode(self, slide_value=20):
        self.software.circuit.RealTimeRadioButton.setChecked(True)
        self.software.circuit.NmaxSlider.setValue(slide_value)

    @staticmethod
    def is_layout_hidden(layout):
        witems = [layout.itemAt(i).widget() for i in range(layout.count())
                  if not isinstance(layout.itemAt(i), QLayout)]
        witems = [witem for witem in witems if witem is not None]
        for witem in witems:
            if not witem.isHidden():
                return False
        return True

    def get_ditems(self):
        return self.software.circuit.Scene.items()

    @property
    def dbuses_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsEllipseItem))])

    @property
    def dlines_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and d.pen().color().name() == '#0000ff')])

    @property
    def dtrafos_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and d.pen().color().name() == '#ff0000')])

    def reset_session(self):
        self.software.startNewSession()

    def load_test_session(self):
        filename = getTestDbFile()
        with open(filename, 'br') as file:
            self.software.createLocalData(file)
            file.close()
        self.software.createSchematic(self.software.circuit.Scene)

    def update_bus_inspector(self, bus):
        self.software.circuit.updateBusInspector(bus)


app = QApplication(sys.argv)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.elegantqt = ElegantQt()
        self.circuit = self.elegantqt.software.circuit

    def test_initial_ui(self):
        self.assertTrue(self.elegantqt.is_layout_hidden(self.circuit.BusLayout), 'BusLayout is not hidden')
        self.assertTrue(self.elegantqt.is_layout_hidden(self.circuit.LineOrTrafoLayout), 'LineOrTrafoLayout is not hidden')
        self.assertTrue(self.elegantqt.is_layout_hidden(self.circuit.InputNewLineType), 'InputNewLineType is not hidden')
        self.assertTrue(self.elegantqt.is_layout_hidden(self.circuit.ControlPanelLayout),
                        'ControlPanelLayout is not hidden')

    def test_insertion_mode(self):
        self.elegantqt.insertion_mode()
        self.assertFalse(self.circuit.RealTimeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: --')
        self.assertEqual(self.circuit.op_mode, 1)

    def test_real_time_mode(self):
        self.elegantqt.real_time_mode(20)
        self.assertFalse(self.circuit.InsertionModeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: {}'.format(self.circuit.nmax).zfill(2))
        self.elegantqt.real_time_mode(5)
        self.assertFalse(self.circuit.InsertionModeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: {}'.format(self.circuit.nmax).zfill(2))

    def test_bus_drawing(self):
        self.elegantqt.software.circuit.Scene.drawBus((0, 0))
        self.assertEqual(1, self.elegantqt.dbuses_amount)
        p = self.elegantqt.software.circuit.Scene.drawBus((1, 0))
        self.assertEqual(type(p), QGraphicsEllipseItem)
        self.assertEqual(0, self.elegantqt.dlines_amount)
        self.assertEqual(0, self.elegantqt.dtrafos_amount)

    def test_bus_clearing(self):
        b = self.elegantqt.software.circuit.Scene.drawBus((0, 0))
        self.assertTrue(type(b) == QGraphicsEllipseItem)
        self.assertEqual(1, self.elegantqt.dbuses_amount)
        pixmap = self.elegantqt.software.circuit.Scene.pixmap
        pixmap[0, 0] = b
        self.elegantqt.software.circuit.Scene.removeItem(pixmap[0, 0])
        self.assertEqual(0, self.elegantqt.dbuses_amount)

    def test_load_session(self):
        self.elegantqt.load_test_session()
        self.assertEqual(18, self.elegantqt.dbuses_amount)

    def test_reset_session(self):
        self.elegantqt.load_test_session()
        self.assertNotEqual(0, self.elegantqt.dbuses_amount)
        self.elegantqt.reset_session()
        self.assertEqual(0, self.elegantqt.dbuses_amount)

    def test_branches_amount(self):
        self.elegantqt.load_test_session()
        self.assertEqual(17, len(self.elegantqt.software.circuit.curves))

    def test_bus_type_change(self):
        self.elegantqt.software.circuit.add_bus()
        bus = self.circuit.system.buses[0]
        self.assertEqual(EARTH, bus.load_ground)
        self.elegantqt.update_bus_inspector(bus)

        # Default case
        self.assertEqual(EARTH_SYMBOL, self.elegantqt.software.circuit.LoadGround.currentText())

        bus.load_ground = DELTA
        # Interface does not change (pl = 0)
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(EARTH_SYMBOL, self.elegantqt.software.circuit.LoadGround.currentText())

        bus.pl = 10

        # Interface changes (pl > 0)
        bus.load_ground = STAR
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(STAR_SYMBOL, self.elegantqt.software.circuit.LoadGround.currentText())

        bus.load_ground = DELTA
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(DELTA_SYMBOL, self.elegantqt.software.circuit.LoadGround.currentText())

        bus.pl = 0
        # Default case (because pl = 0)
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(EARTH_SYMBOL, self.elegantqt.software.circuit.LoadGround.currentText())


if __name__ == '__main__':
    unittest.main()
