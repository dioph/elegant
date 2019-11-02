import unittest

from PyQt5.QtWidgets import *

from aspy.interface import ASPy
from ..utils import *


class ASPyQt(QWidget):
    def __init__(self):
        super(ASPyQt, self).__init__()
        self.ASPy = ASPy()
        self.ASPy.initUI()

    def insertion_mode(self):
        self.ASPy.circuit.InsertionModeRadioButton.setChecked(True)

    def real_time_mode(self, slide_value=20):
        self.ASPy.circuit.RealTimeRadioButton.setChecked(True)
        self.ASPy.circuit.NmaxSlider.setValue(slide_value)

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
        return self.ASPy.circuit.Scene.items()

    @property
    def dbuses_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if isinstance(d, QGraphicsPixmapItem)])

    @property
    def dlines_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and d.pen().color().name() == '#0000ff')])

    @property
    def dxmfrs_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and d.pen().color().name() == '#ff0000')])


app = QApplication(sys.argv)


class ASPyTests(unittest.TestCase):
    def setUp(self):
        self.aspyqt = ASPyQt()
        self.circuit = self.aspyqt.ASPy.circuit

    def test_initial_ui(self):
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.BusLayout), 'BusLayout is not hidden')
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.LineOrTrafoLayout), 'LineOrTrafoLayout is not hidden')
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.InputNewLineType), 'InputNewLineType is not hidden')
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.ControlPanelLayout),
                        'ControlPanelLayout is not hidden')

    def test_insertion_mode(self):
        self.aspyqt.insertion_mode()
        self.assertFalse(self.circuit.RealTimeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: --')
        self.assertEqual(self.circuit.op_mode, 1)

    def test_real_time_mode(self):
        self.aspyqt.real_time_mode(20)
        self.assertFalse(self.circuit.InsertionModeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: {}'.format(self.circuit.nmax).zfill(2))
        self.aspyqt.real_time_mode(5)
        self.assertFalse(self.circuit.InsertionModeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: {}'.format(self.circuit.nmax).zfill(2))

    def test_load_session(self):
        self.test_initial_ui()
        file = getTestDbFile()
        with open(file, 'br') as file:
            self.aspyqt.ASPy.createLocalData(file)
            file.close()
        self.aspyqt.ASPy.createSchematic(self.aspyqt.ASPy.circuit.Scene)
        self.assertGreater(len(self.aspyqt.ASPy.circuit.system.buses), 0, 'buses = 0')
        self.assertGreater(len(self.aspyqt.ASPy.circuit.system.lines), 0, 'lines = 0')
        self.assertGreater(len(self.aspyqt.ASPy.circuit.system.trafos), 0,  'trafos > 0')


if __name__ == '__main__':
    unittest.main()
