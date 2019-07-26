import unittest

from PyQt5.QtCore import QRect, QLine
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

    @property
    def dbuses_amount(self):
        ditems = self.ASPy.circuit.Scene.children()
        print(ditems)
        return len([d for d in ditems if isinstance(d, QRect)])

    @property
    def dlines_amout(self):
        ditems = self.ASPy.circuit.Scene.children()
        return len([d for d in ditems if isinstance(d, QLine)])


app = QApplication(sys.argv)


class ASPyTests(unittest.TestCase):
    def setUp(self):
        self.aspyqt = ASPyQt()
        self.circuit = self.aspyqt.ASPy.circuit

    def test_initial_ui(self):
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.BusLayout), 'BusLayout is not hidden')
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.LineOrXfmrLayout), 'LineOrXfmrLayout is not hidden')
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.InputNewLineType), 'InputNewLineType is not hidden')
        self.assertTrue(self.aspyqt.is_layout_hidden(self.circuit.ControlPanelLayout),
                        'ControlPanelLayout is not hidden')
        self.assertEqual(self.aspyqt.dbuses_amount, 0, 'amount of buses > 0')

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
        file = getTestDbFile()
        with open(file, 'br') as file:
            self.aspyqt.ASPy.createLocalData(file)
            file.close()
        self.assertGreater(len(self.aspyqt.ASPy.circuit.system.buses), 0, 'Incorrect amount of buses encountered')
        self.assertGreater(len(self.aspyqt.ASPy.circuit.system.lines), 0, 'Incorrect amount of lines encountered')
        self.assertFalse(len(self.aspyqt.ASPy.circuit.system.xfmrs) > 0, 'Incorrect amount of xmfrs encountered')

if __name__ == '__main__':
    unittest.main()
