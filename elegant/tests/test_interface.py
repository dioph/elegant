import sys
import unittest

from PyQt5.QtWidgets import QWidget, QLayout, QApplication, \
    QGraphicsEllipseItem, QGraphicsLineItem

from elegant.interface import Window
from elegant.utils import getTestDbFile


class ElegantQt(QWidget):
    def __init__(self, *args, **kwargs):
        super(ElegantQt, self).__init__(*args, *kwargs)
        self.window = Window()
        self.window.init_ui()

    @staticmethod
    def is_layout_hidden(layout):
        widgets = [layout.itemAt(i).widget() for i in range(layout.count())
                   if not isinstance(layout.itemAt(i), QLayout)]
        widgets = [item for item in widgets if item is not None]
        for item in widgets:
            if not item.isHidden():
                return False
        return True

    def get_ditems(self):
        return self.window.main_widget.editor.items()

    @property
    def dbuses_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsEllipseItem))])

    @property
    def dlines_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and
                                          d.pen().color().name() == '#0000ff')])

    @property
    def dtrafos_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and
                                          d.pen().color().name() == '#ff0000')])

    def reset_session(self):
        self.window.start_new_session()

    def load_test_session(self):
        filename = getTestDbFile()
        with open(filename, 'br') as file:
            self.window.create_local_data(file)
            file.close()
        self.window.create_schematic(self.window.main_widget.editor)

    def update_bus_inspector(self, bus):
        self.window.main_widget.bus_menu(bus)


app = QApplication(sys.argv)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.elegantqt = ElegantQt()
        self.main_widget = self.elegantqt.window.main_widget

    def test_initial_ui(self):
        pass

    def test_bus_drawing(self):
        self.elegantqt.window.main_widget.editor.draw_bus((0, 0))
        self.assertEqual(1, self.elegantqt.dbuses_amount)
        p = self.elegantqt.window.main_widget.editor.draw_bus((1, 0))
        self.assertEqual(type(p), QGraphicsEllipseItem)
        self.assertEqual(0, self.elegantqt.dlines_amount)
        self.assertEqual(0, self.elegantqt.dtrafos_amount)

    def test_bus_clearing(self):
        b = self.elegantqt.window.main_widget.editor.draw_bus((0, 0))
        self.assertTrue(type(b) == QGraphicsEllipseItem)
        self.assertEqual(1, self.elegantqt.dbuses_amount)
        drawings = self.elegantqt.window.main_widget.editor.drawings
        drawings[0, 0] = b
        self.elegantqt.window.main_widget.editor.removeItem(drawings[0, 0])
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
        self.assertEqual(17, len(self.elegantqt.window.main_widget.curves))

    def test_bus_type_change(self):
        pass

    def test_create_local_data(self):
        self.elegantqt.load_test_session()
        for bus in self.main_widget.system.buses:
            self.assertIn(bus, self.main_widget.editor.bus_grid)
        for curve in self.main_widget.curves:
            self.assertTrue(curve.obj in self.main_widget.system.lines or
                            curve.obj in self.main_widget.system.trafos)

    def test_empty_string_input(self):
        pass


if __name__ == '__main__':
    unittest.main()
