import unittest

from PyQt5.QtWidgets import *

from elegant.interface import Window, STAR, EARTH, DELTA, STAR_SYMBOL, EARTH_SYMBOL, DELTA_SYMBOL
from ..utils import *


class ElegantQt(QWidget):
    def __init__(self, *args, **kwargs):
        super(ElegantQt, self).__init__(*args, *kwargs)
        self.window = Window()
        self.window.initUI()

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
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and d.pen().color().name() == '#0000ff')])

    @property
    def dtrafos_amount(self):
        ditems = self.get_ditems()
        return len([d for d in ditems if (isinstance(d, QGraphicsLineItem) and d.pen().color().name() == '#ff0000')])

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
        self.assertTrue(self.elegantqt.is_layout_hidden(self.main_widget.bus_layout),
                        "BusLayout is not hidden")
        self.assertTrue(self.elegantqt.is_layout_hidden(self.main_widget.line_or_trafo_layout),
                        "LineOrTrafoLayout is not hidden")
        self.assertTrue(self.elegantqt.is_layout_hidden(self.main_widget.new_line_type),
                        "InputNewLineType is not hidden")
        self.assertTrue(self.elegantqt.is_layout_hidden(self.main_widget.control_panel_layout),
                        "ControlPanelLayout is not hidden")

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
        self.elegantqt.window.main_widget.add_bus()
        bus = self.main_widget.system.buses[0]
        self.assertEqual(EARTH, bus.load_ground)
        self.elegantqt.update_bus_inspector(bus)

        # Default case
        self.assertEqual(EARTH_SYMBOL, self.elegantqt.window.main_widget.load_ground.currentText())

        bus.load_ground = DELTA
        # Interface does not change (pl = 0)
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(EARTH_SYMBOL, self.elegantqt.window.main_widget.load_ground.currentText())

        bus.pl = 10

        # Interface changes (pl > 0)
        bus.load_ground = STAR
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(STAR_SYMBOL, self.elegantqt.window.main_widget.load_ground.currentText())

        bus.load_ground = DELTA
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(DELTA_SYMBOL, self.elegantqt.window.main_widget.load_ground.currentText())

        bus.pl = 0
        # Default case (because pl = 0)
        self.elegantqt.update_bus_inspector(bus)
        self.assertEqual(EARTH_SYMBOL, self.elegantqt.window.main_widget.load_ground.currentText())


if __name__ == '__main__':
    unittest.main()
