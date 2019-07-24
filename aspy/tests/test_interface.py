import sys
import unittest
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtCore import QRect, QLine, QPoint
from time import sleep

from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

from aspy.interface import ASPy
import aspy.interface_automation as ia


class ASPyQt(QWidget):
    def __init__(self):
        super(ASPyQt, self).__init__()
        self.ui = ASPy()
        self.ui.initUI()

    def insertion_mode(self):
        self.ui.circuit.InsertionModeRadioButton.setChecked(True)

    def real_time_mode(self, slide_value=20):
        self.ui.circuit.RealTimeRadioButton.setChecked(True)
        self.ui.circuit.NmaxSlider.setValue(slide_value)

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
        ditems = self.ui.circuit.Scene.children()
        return len([d for d in ditems if isinstance(d, QRect)])

    @property
    def dlines_amout(self):
        ditems = self.ui.circuit.Scene.children()
        return len([d for d in ditems if isinstance(d, QLine)])


app = QApplication(sys.argv)


class ASPyTests(unittest.TestCase):
    def setUp(self):
        self.aspy = ASPyQt()
        self.circuit = self.aspy.ui.circuit

    def test_initial_ui(self):
        self.assertTrue(self.aspy.is_layout_hidden(self.circuit.BusLayout), 'BusLayout is not hidden')
        self.assertTrue(self.aspy.is_layout_hidden(self.circuit.LineOrXfmrLayout), 'LineOrXfmrLayout is not hidden')
        self.assertTrue(self.aspy.is_layout_hidden(self.circuit.InputNewLineType), 'InputNewLineType is not hidden')
        self.assertTrue(self.aspy.is_layout_hidden(self.circuit.ControlPanelLayout), 'ControlPanelLayout is not hidden')
        self.assertEqual(self.aspy.dbuses_amount, 0, 'amount of buses > 0')

    def test_insertion_mode(self):
        self.aspy.insertion_mode()
        self.assertFalse(self.circuit.RealTimeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: --')
        self.assertEqual(self.circuit.op_mode, 1)

    def test_real_time_mode(self):
        self.aspy.real_time_mode(20)
        self.assertFalse(self.circuit.InsertionModeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: {}'.format(self.circuit.nmax).zfill(2))
        self.aspy.real_time_mode(5)
        self.assertFalse(self.circuit.InsertionModeRadioButton.isChecked())
        self.assertEqual(self.circuit.NmaxLabel.text(), 'Nmax: {}'.format(self.circuit.nmax).zfill(2))

    def test_bus_insertion(self):
        self.aspy.add_dbus((0, 9))
        self.assertEqual(self.aspy.dbuses_amount, 1)


if __name__ == '__main__':
    unittest.main()
