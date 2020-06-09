import pickle
import shutil
import sys

import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt, QRegExp
from PyQt5.QtGui import QPen, QBrush, QDoubleValidator, QRegExpValidator, QIntValidator
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QHBoxLayout, \
    QVBoxLayout, QLayout, QRadioButton, QGroupBox, QFormLayout, QLineEdit, QComboBox, \
    QPushButton, QSlider, QLabel, QCheckBox, QMainWindow, QAction, QFileDialog, \
    QApplication

from .core import Bus, TransmissionLine, Transformer, PowerSystem
from .report import create_report
from .utils import LineSegment, getSessionsDir, safe_repr, interface_coordpairs

STAR = 0
EARTH = 1
DELTA = 2
STAR_SYMBOL = "Y"
EARTH_SYMBOL = "Y\u23DA"
DELTA_SYMBOL = "\u0394"

PY_TO_SYMBOL = {STAR: STAR_SYMBOL, EARTH: EARTH_SYMBOL, DELTA: DELTA_SYMBOL}
SYMBOL_TO_PY = {STAR_SYMBOL: STAR, EARTH_SYMBOL: EARTH, DELTA_SYMBOL: DELTA}


class Block:
    def __init__(self, start=False, end=True):
        self.start = start
        self.end = end


class HistoryData:
    def __init__(self, current=None, last=None):
        self.current = current
        self.last = last

    def __gt__(self, other):
        if self.is_current_empty or self.is_last_empty:
            return False
        return np.all(self.current) > other and np.all(self.last) > other

    @property
    def is_current_empty(self):
        return self.current is None

    @property
    def is_last_empty(self):
        return self.last is None

    @property
    def is_empty(self):
        return (self.last, self.current) == (None, None)

    @property
    def is_full(self):
        return self.last is not None and self.current is not None

    @property
    def allows_drawing(self):
        return self.is_full and self.current != self.last

    def reset(self):
        self.last = None
        self.current = None

    def is_last_different_from(self, x, y):
        return self.last[0] != x or self.last[1] != y

    def is_current_different_from(self, x, y):
        return self.current[0] != x or self.current[1] != y

    def set_last(self, x, y):
        self.last = [x, y]

    def set_current(self, x, y):
        self.current = [x, y]


class ScrollView(QGraphicsView):
    def __init__(self, scene):
        super(ScrollView, self).__init__(scene)
        self.horizontalScrollBar().valueChanged.connect(self.erase)
        self.verticalScrollBar().valueChanged.connect(self.erase)

    def erase(self):
        if self.scene().cursor is not None:
            self.scene().removeItem(self.scene().cursor)
            self.scene().cursor = None


class Editor(QGraphicsScene):
    """Overwrites mouse events of a QGraphicsScene object to enable drawing
    the network within a grid-like canvas
    """
    pointer_signal = pyqtSignal(object)
    method_signal = pyqtSignal(object)
    data_signal = pyqtSignal(object)

    def __init__(self, size=20, length=50):
        super(Editor, self).__init__()
        self.size = size
        self.view = ScrollView(self)

        # System state variables
        self.drawings = np.zeros((self.size, self.size), object)
        self.bus_grid = np.zeros((self.size, self.size), object)
        self.square_length = length
        self.circle_radius = length / 2
        self.move_history = HistoryData()
        self.block = Block()
        self.selectorHistory = HistoryData()
        self.cursor = None

        # Visible portion of Scene to View
        self.setSceneRect(0, 0,
                          self.square_length * self.size,
                          self.square_length * self.size)
        self.coord_grid = np.array([[[int(length * (i + .5)),
                                      int(length * (j + .5))]
                                     for i in range(size)]
                                    for j in range(size)])
        self.draw_grid()
        self.setSceneRect(self.square_length * -2,
                          self.square_length * -2,
                          self.square_length * (self.size + 4),
                          self.square_length * (self.size + 4))

    def draw_grid(self):
        """Display the quantized interface guidelines"""
        width, height = self.width(), self.height()
        boundaries = self.coord_grid[0, :, 0] - self.square_length / 2
        pen = QPen()
        pen.setColor(Qt.lightGray)
        pen.setStyle(Qt.DashDotDotLine)
        for boundary in boundaries:
            # Horizontal lines
            self.addLine(0.0, boundary, width, boundary, pen)
            # Vertical lines
            self.addLine(boundary, 0.0, boundary, height, pen)
        self.addLine(0.0, height, width, height, pen)
        self.addLine(width, 0.0, width, height, pen)

    def draw_line(self, coord_1, coord_2, color='b'):
        """
        Parameters
        ----------
        coord_1, coord_2: line end points
        color:  'b' = blue pen (line)
                'r' = red pen (trafo)

        Returns
        -------
        line: drawn line (PyQt5 object)
        """
        pen = QPen()
        pen.setWidthF(2.5)
        if color == 'b':
            pen.setColor(Qt.blue)
        elif color == 'r':
            pen.setColor(Qt.red)
        line = self.addLine(coord_1[0], coord_1[1], coord_2[0], coord_2[1], pen)
        return line

    def draw_square(self, coord):
        """
        Parameters
        ----------
        coord: square top-left corner

        Returns
        -------
        QRect: drawn square (PyQt5 object)
        """
        pen = QPen(Qt.yellow)
        brush = QBrush(Qt.yellow, Qt.Dense7Pattern)
        x, y = coord
        rect = self.addRect(x, y,
                            self.square_length, self.square_length,
                            pen, brush)
        return rect

    def draw_bus(self, coord):
        x, y = np.array(coord) - self.circle_radius / 2
        pen = QPen(Qt.black)
        brush = QBrush(Qt.SolidPattern)
        circle = self.addEllipse(x, y,
                                 self.circle_radius, self.circle_radius,
                                 pen, brush)
        return circle

    def get_central_point(self, coord):
        legs = self.coord_grid - coord
        good = (np.hypot(legs[:, :, 0], legs[:, :, 1]) < self.circle_radius)
        i, j = good.nonzero()
        if i.size > 0 and j.size > 0:
            return i[0], j[0]
        return None

    def redraw_cursor(self, x, y):
        if self.cursor is not None:
            self.removeItem(self.cursor)
        self.selectorHistory.set_current(x - self.square_length / 2,
                                         y - self.square_length / 2)
        self.cursor = self.draw_square(self.selectorHistory.current)

    def is_drawing_blocked(self):
        return self.block.start or \
               self.block.end or \
               not self.move_history.allows_drawing

    def mouseReleaseEvent(self, event):
        self.move_history.reset()
        self.block.start = True
        self.block.end = False
        self.method_signal.emit('UPDATE')

    def mouseDoubleClickEvent(self, event):
        coord = [event.scenePos().x(), event.scenePos().y()]
        if self.get_central_point(coord) is not None:
            i, j = self.get_central_point(coord)
            x, y = self.coord_grid[i, j]
            circle = self.draw_bus((x, y))
            self.drawings[i, j] = circle
            self.pointer_signal.emit((i, j))
            self.method_signal.emit('ADD_BUS')

    def mousePressEvent(self, event):
        coord = [event.scenePos().x(), event.scenePos().y()]
        if self.get_central_point(coord) is not None:
            i, j = self.get_central_point(coord)
            x, y = self.coord_grid[i, j]
            self.redraw_cursor(x, y)
            self.pointer_signal.emit((i, j))
            self.method_signal.emit('START_LINE')
            self.method_signal.emit('LAYOUT')

    def mouseMoveEvent(self, event):
        coord = [event.scenePos().x(), event.scenePos().y()]
        if self.get_central_point(coord) is not None:
            i, j = self.get_central_point(coord)
            x, y = self.coord_grid[i, j]
            self.redraw_cursor(x, y)
            if self.move_history.is_empty:
                self.move_history.set_last(x, y)
                if isinstance(self.bus_grid[i, j], Bus):
                    self.block.start = False
            if self.move_history.is_last_different_from(x, y):
                self.move_history.set_current(x, y)
            if not self.is_drawing_blocked():
                coord_1 = self.move_history.last
                coord_2 = self.move_history.current
                line = self.draw_line(coord_1, coord_2, color='b')
                self.move_history.reset()
                self.pointer_signal.emit((i, j))
                self.data_signal.emit(line)
                self.method_signal.emit('APPEND')
                if isinstance(self.bus_grid[i, j], Bus):
                    self.block.end = True


class MainWidget(QWidget):
    status_msg = pyqtSignal(object)

    def __init__(self, parent=None, editor_square_length=50):
        # General initializations
        super(MainWidget, self).__init__(parent)
        self.system = PowerSystem()
        self.line_types = {"Default": TransmissionLine(orig=None, dest=None)}
        self.curves = []
        self.max_niter = 20

        self.editor = Editor(length=editor_square_length)

        self.view = self.editor.view
        self.editor_layout = QHBoxLayout()  # Layout for editor
        self.editor_layout.addWidget(self.view)
        self._curr_element_coord = None  # Coordinates to current object
        self._start_line = True
        self._line_origin = None
        self._temp = None
        self.__calls = {'ADD_BUS': self.add_bus,
                        'APPEND': self.add_segment,
                        'LAYOUT': self.update_layout,
                        'UPDATE': self.update_values,
                        'START_LINE': self.store_line_origin}
        self.editor.pointer_signal.connect(self.set_current_coord)
        self.editor.data_signal.connect(self.set_temp)
        self.editor.method_signal.connect(self.methods_trigger)

        # Inspectors
        self.left_sidebar_layout = QHBoxLayout()
        self.left_sidebar_widget = QWidget()
        self.left_sidebar_widget.setLayout(self.left_sidebar_layout)
        self.right_sidebar_layout = QHBoxLayout()
        self.top_layout = QHBoxLayout()
        self.top_layout.addWidget(self.left_sidebar_widget)
        self.top_layout.addLayout(self.editor_layout)
        self.top_layout.addLayout(self.right_sidebar_layout)
        self.setLayout(self.top_layout)
        self.no_menu()

    def methods_trigger(self, args):
        """Trigger methods defined in __calls"""
        self.__calls[args]()

    def set_current_coord(self, args):
        """Define coordinates pointing to current selected object in interface"""
        self._curr_element_coord = args

    def set_temp(self, args):
        """This method stores the first line in line element drawing during line
        inputting. Its existence is justified by the first square limitation in
        MouseMoveEvent
        """
        self._temp = args

    def store_line_origin(self):
        if self._start_line:
            self._line_origin = self._curr_element_coord

    def clear_layout(self, layout):
        """Hide completely any layout containing widgets or/and other layouts"""
        widgets = list(layout.itemAt(i).widget() for i in range(layout.count())
                       if not isinstance(layout.itemAt(i), QLayout))
        widgets = list(filter(lambda x: x is not None, widgets))
        for w in widgets:
            w.setHidden(True)
        layouts = list(layout.itemAt(i).layout() for i in range(layout.count())
                       if isinstance(layout.itemAt(i), QLayout))
        for child_layout in layouts:
            self.clear_layout(child_layout)
            layout.removeItem(child_layout)

    def set_nmax(self, nmax, nmax_label):
        self.max_niter = nmax
        nmax_label.setText("Nmax: {:02d}".format(self.max_niter))

    def bus_at(self, coord):
        """Returns a Bus object that occupies grid in `coord` position"""
        grid_bus = self.editor.bus_grid[coord]
        if isinstance(grid_bus, Bus):
            return grid_bus
        return None

    def curve_at(self, coord):
        """Returns a LineSegment object that has `coord` in its coordinates"""
        for curve in self.curves:
            if coord in curve.coords:
                return curve
        return None

    def are_lines_crossing(self):
        """Searches for crossing between current inputting line/trafo and existent line/trafo"""
        is_bus = isinstance(self.editor.bus_grid[self._curr_element_coord], Bus)
        for curve in self.curves:
            if self._curr_element_coord in curve.coords and not is_bus:
                return True
        return False

    def add_segment(self):
        if self._start_line:
            bus_orig = self.editor.bus_grid[self._line_origin]
            new_line = TransmissionLine(orig=bus_orig, dest=None)
            new_curve = LineSegment(obj=new_line,
                                    coords=[self._line_origin,
                                            self._curr_element_coord],
                                    dlines=[self._temp])
            if self.are_lines_crossing():
                new_curve.remove = True
            self.curves.append(new_curve)
        else:
            curr_curve = self.curves[-1]
            if self.are_lines_crossing():
                curr_curve.remove = True
            curr_curve.dlines.append(self._temp)
            curr_curve.coords.append(self._curr_element_coord)
            if isinstance(self.editor.bus_grid[self._curr_element_coord], Bus):
                if curr_curve.obj.dest is None:
                    bus_dest = self.editor.bus_grid[self._curr_element_coord]
                    curr_curve.obj.dest = bus_dest
        self._start_line = False
        self.status_msg.emit("Adding line...")

    def find_line_model(self, line):
        """Return the name of parameters set of a existent line or
        return "No model" if the line has been set by impedance and admittance
        """
        for line_name, line_model in self.line_types.items():
            if line_model.param == line.param:
                return line_name
        return "No model"

    def add_new_line_model(self, name, new_param):
        """Add a new type of line, if given parameters has passed in all the tests
        Called by: SubmitNewLineTypePushButton.pressed"""
        line = TransmissionLine(orig=None, dest=None)
        line.__dict__.update(new_param)
        if name in self.line_types.keys():
            self.status_msg.emit("Duplicated name. Insert another valid name")
            return
        if any(np.isnan(list(new_param.values()))):
            self.status_msg.emit("Undefined parameter. Fill all parameters")
            return
        if any(map(lambda x: line.param == x.param, self.line_types.values())):
            self.status_msg.emit("A similar model was identified. The model has not been stored")
            return
        self.line_types[name] = line
        self.status_msg.emit("The model has been stored")

    def submit_line_by_model(self, line_model, ell, vbase):
        """Update a line with parameters

        Parameters
        ----------
        line_model: TL object with data to update line
        ell: line length (m)
        vbase: voltage base (V)
        """
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, TransmissionLine):
            line = curve.obj
            line.Z, line.Y = None, None
            line.__dict__.update(line_model.param)
            line.vbase = vbase
            line.ell = ell
            self.status_msg.emit("Updated line with model")
        elif isinstance(curve.obj, Transformer):
            trafo = curve.obj
            self.remove_trafo(curve)
            new_line = TransmissionLine(orig=trafo.orig, dest=trafo.dest)
            new_line.Z, new_line.Y = None, None
            new_line.__dict__.update(line_model.param)
            new_line.vbase = vbase
            new_line.ell = ell
            self.status_msg.emit("Trafo -> line, updated with model")
            new_curve = LineSegment(obj=new_line,
                                    dlines=curve.dlines,
                                    coords=curve.coords)
            for line_drawing in new_curve.dlines:
                blue_pen = QPen()
                blue_pen.setColor(Qt.blue)
                blue_pen.setWidthF(2.5)
                line_drawing.setPen(blue_pen)
                self.editor.addItem(line_drawing)
                self.add_line(new_curve)
        self.update_values()

    def submit_line_by_impedance(self, tl_r, tl_x, tl_b, ell, vbase):
        """Update a line with impedance/admittance

        Parameters
        ----------
        tl_r: resistance (ohm)
        tl_x: reactance (ohm)
        tl_b: susceptance (mho)
        ell: line length (m)
        vbase: voltage base (V)
        """
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, TransmissionLine):
            line = curve.obj
            tl_z = tl_r + 1j * tl_x
            tl_y = 1j * tl_b
            zbase = vbase ** 2 / 1e8
            line.Z, line.Y = tl_z * zbase, tl_y / zbase
            line.ell = ell
            line.vbase = vbase
            line.m = 0
            self.status_msg.emit("Updated line with impedance")
        elif isinstance(curve.obj, Transformer):
            trafo = curve.obj
            self.remove_trafo(curve)
            new_line = TransmissionLine(orig=trafo.orig, dest=trafo.dest)
            tl_z = tl_r + 1j * tl_x
            tl_y = 1j * tl_b
            zbase = vbase ** 2 / 1e8
            new_line.Z, new_line.Y = tl_z * zbase, tl_y / zbase
            new_line.ell = ell
            new_line.vbase = vbase
            new_line.m = 0
            self.status_msg.emit("Trafo -> line, updated with impedance")
            new_curve = LineSegment(obj=new_line,
                                    dlines=curve.dlines,
                                    coords=curve.coords)
            for line_drawing in new_curve.dlines:
                blue_pen = QPen()
                blue_pen.setColor(Qt.blue)
                blue_pen.setWidthF(2.5)
                line_drawing.setPen(blue_pen)
                self.editor.addItem(line_drawing)
            self.add_line(new_curve)
        self.update_values()

    def toggle_line_trafo(self, check):
        """Show line or trafo options in adding line/trafo section"""
        if check:
            self.line_menu()
        else:
            self.trafo_menu()

    def no_menu(self):
        no_layout = QHBoxLayout()
        self.clear_layout(self.left_sidebar_layout)
        self.clear_layout(self.right_sidebar_layout)
        self.left_sidebar_layout.addLayout(no_layout)

    def trafo_menu(self):
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, TransmissionLine):
            trafo = Transformer(orig=None, dest=None)
        else:
            trafo = curve.obj
        trafo_layout = QVBoxLayout()

        choose_line = QRadioButton('TL')
        choose_trafo = QRadioButton('TRAFO')
        choose_trafo.setChecked(True)
        choose_line.toggled.connect(self.toggle_line_trafo)

        choose_line_or_trafo_box = QGroupBox("")
        choose_line_or_trafo = QHBoxLayout()
        choose_line_or_trafo.addWidget(choose_line)
        choose_line_or_trafo.addWidget(choose_trafo)
        choose_line_or_trafo_box.setLayout(choose_line_or_trafo)

        trafo_form_layout = QFormLayout()
        s_nom_trafo_line_edit = QLineEdit(safe_repr(trafo.snom, 1e6))
        s_nom_trafo_line_edit.setValidator(QDoubleValidator(bottom=0.))
        x_zero_seq_trafo_line_edit = QLineEdit(safe_repr(trafo.jx0, 0.01))
        x_zero_seq_trafo_line_edit.setValidator(QDoubleValidator(bottom=0.))
        x_pos_seq_trafo_line_edit = QLineEdit(safe_repr(trafo.jx1, 0.01))
        x_pos_seq_trafo_line_edit.setValidator(QDoubleValidator(bottom=0.))

        trafo_primary = QComboBox()
        trafo_primary.addItem('Y')
        trafo_primary.addItem('Y\u23DA')
        trafo_primary.addItem('\u0394')
        trafo_secondary = QComboBox()
        trafo_secondary.addItem('Y')
        trafo_secondary.addItem('Y\u23DA')
        trafo_secondary.addItem('\u0394')
        trafo_primary.setCurrentText(PY_TO_SYMBOL[trafo.primary])
        trafo_secondary.setCurrentText(PY_TO_SYMBOL[trafo.secondary])

        def submit_trafo():
            snom = float(s_nom_trafo_line_edit.text()) * 1e6
            x0 = float(x_zero_seq_trafo_line_edit.text()) / 100
            x1 = float(x_pos_seq_trafo_line_edit.text()) / 100
            primary = SYMBOL_TO_PY[trafo_primary.currentText()]
            secondary = SYMBOL_TO_PY[trafo_secondary.currentText()]
            self.submit_trafo(snom, x0, x1, primary, secondary)

        trafo_submit_push_button = QPushButton("Submit trafo")
        trafo_submit_push_button.pressed.connect(submit_trafo)

        remove_trafo_push_button = QPushButton("Remove trafo")
        remove_trafo_push_button.pressed.connect(self.remove_trafo)
        """
        Reason of direct button bind to self.update_layout:
        The layout should disappear only when a line or trafo is excluded.
        The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        remove_trafo_push_button.pressed.connect(self.update_layout)

        trafo_form_layout.addRow("Snom (MVA)", s_nom_trafo_line_edit)
        trafo_form_layout.addRow("x+ (%pu)", x_pos_seq_trafo_line_edit)
        trafo_form_layout.addRow("x0 (%pu)", x_zero_seq_trafo_line_edit)
        trafo_form_layout.addRow("Prim.", trafo_primary)
        trafo_form_layout.addRow("Sec.", trafo_secondary)

        trafo_layout.addStretch()
        trafo_layout.addWidget(choose_line_or_trafo_box)
        trafo_layout.addLayout(trafo_form_layout)

        # Buttons submit and remove button for trafo
        trafo_layout.addWidget(trafo_submit_push_button)
        trafo_layout.addWidget(remove_trafo_push_button)
        trafo_layout.addStretch()

        self.clear_layout(self.left_sidebar_layout)
        self.left_sidebar_layout.addLayout(trafo_layout)

    def line_menu(self):
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, Transformer):
            line = self.line_types['Default']
        else:
            line = curve.obj
        line_model = self.find_line_model(line)

        line_layout = QVBoxLayout()

        choose_line = QRadioButton('TL')
        choose_line.setChecked(True)
        choose_trafo = QRadioButton('TRAFO')
        choose_line.toggled.connect(self.toggle_line_trafo)

        choose_line_or_trafo_box = QGroupBox("")
        choose_line_or_trafo = QHBoxLayout()
        choose_line_or_trafo.addWidget(choose_line)
        choose_line_or_trafo.addWidget(choose_trafo)
        choose_line_or_trafo_box.setLayout(choose_line_or_trafo)

        line_form_layout = QFormLayout()

        choose_line_model = QComboBox()
        choose_line_model.addItem("No model")
        for model in self.line_types:
            choose_line_model.addItem(model)
        choose_line_model.setCurrentText(line_model)

        ell_line_edit = QLineEdit(safe_repr(line.ell, 1000))
        ell_line_edit.setValidator(QDoubleValidator(bottom=0.))
        vbase_line_edit = QLineEdit(safe_repr(line.vbase, 1000))
        vbase_line_edit.setValidator(QDoubleValidator(bottom=0.))
        tl_r_line_edit = QLineEdit(safe_repr(line.Zpu.real, 0.01, "{:.4f}"))
        tl_r_line_edit.setValidator(QDoubleValidator(bottom=0.))
        tl_x_line_edit = QLineEdit(safe_repr(line.Zpu.imag, 0.01, "{:.4f}"))
        tl_x_line_edit.setValidator(QDoubleValidator(bottom=0.))
        tl_b_line_edit = QLineEdit(safe_repr(line.Ypu.imag, 0.01, "{:.4f}"))
        tl_b_line_edit.setValidator(QDoubleValidator(bottom=0.))

        def submit_line_by_impedance():
            tl_r = float(tl_r_line_edit.text()) / 100
            tl_x = float(tl_x_line_edit.text()) / 100
            tl_b = float(tl_b_line_edit.text()) / 100
            ell = float(ell_line_edit.text()) * 1e3
            vbase = float(vbase_line_edit.text()) * 1e3
            self.submit_line_by_impedance(tl_r, tl_x, tl_b, ell, vbase)
        tl_submit_by_impedance_button = QPushButton("Submit by impedance")
        tl_submit_by_impedance_button.pressed.connect(submit_line_by_impedance)

        def submit_line_by_model():
            selected_model = self.line_types[choose_line_model.currentText()]
            ell = float(ell_line_edit.text()) * 1e3
            vbase = float(vbase_line_edit.text()) * 1e3
            self.submit_line_by_model(selected_model, ell, vbase)
        tl_submit_by_model_button = QPushButton("Submit by model")
        tl_submit_by_model_button.pressed.connect(submit_line_by_model)

        line_form_layout.addRow("Model", choose_line_model)
        line_form_layout.addRow("\u2113 (km)", ell_line_edit)
        line_form_layout.addRow("Vbase (kV)", vbase_line_edit)
        line_form_layout.addRow("R (%pu)", tl_r_line_edit)
        line_form_layout.addRow("X<sub>L</sub> (%pu)", tl_x_line_edit)
        line_form_layout.addRow("B<sub>C</sub> (%pu)", tl_b_line_edit)

        remove_tl_push_button = QPushButton("Remove TL")
        remove_tl_push_button.pressed.connect(self.remove_line)
        """
        Reason of direct button bind to self.update_layout:
        The layout should disappear only when a line or trafo is excluded.
        The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        remove_tl_push_button.pressed.connect(self.update_layout)

        line_layout.addStretch()
        line_layout.addWidget(choose_line_or_trafo_box)
        line_layout.addLayout(line_form_layout)

        # Submit and remove buttons for line
        line_layout.addWidget(tl_submit_by_model_button)
        line_layout.addWidget(tl_submit_by_impedance_button)
        line_layout.addWidget(remove_tl_push_button)
        line_layout.addStretch()

        self.clear_layout(self.left_sidebar_layout)
        self.left_sidebar_layout.addLayout(line_layout)

    def new_line_model_menu(self):
        # Layout for input new type of line
        new_line_type = QVBoxLayout()
        new_line_type_form_layout = QFormLayout()

        model_name = QLineEdit()
        model_name.setValidator(QRegExpValidator(QRegExp("[A-Za-z]*")))
        rho_line_edit = QLineEdit()
        rho_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        r_line_edit = QLineEdit()
        r_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        d12_line_edit = QLineEdit()
        d12_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        d23_line_edit = QLineEdit()
        d23_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        d31_line_edit = QLineEdit()
        d31_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        d_line_edit = QLineEdit()
        d_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        m_line_edit = QLineEdit()
        m_line_edit.setValidator(QIntValidator(bottom=1, top=4))
        imax_line_edit = QLineEdit()
        imax_line_edit.setValidator(QDoubleValidator(bottom=0.))

        new_line_type_form_layout.addRow("Name", model_name)
        new_line_type_form_layout.addRow("\u03C1 (n\u03A9m)", rho_line_edit)
        new_line_type_form_layout.addRow("r (mm)", r_line_edit)
        new_line_type_form_layout.addRow("d12 (m)", d12_line_edit)
        new_line_type_form_layout.addRow("d23 (m)", d23_line_edit)
        new_line_type_form_layout.addRow("d31 (m)", d31_line_edit)
        new_line_type_form_layout.addRow("d (m)", d_line_edit)
        new_line_type_form_layout.addRow("m", m_line_edit)
        new_line_type_form_layout.addRow("Imax (A)", imax_line_edit)

        new_line_type.addStretch()
        new_line_type.addLayout(new_line_type_form_layout)

        def add_new_line_model():
            name = model_name.text()

            def float_or_nan(s):
                return np.nan if s == '' else float(s)
            new_param = dict(
                r=float_or_nan(r_line_edit.text()) / 1e3,
                d12=float_or_nan(d12_line_edit.text()),
                d23=float_or_nan(d23_line_edit.text()),
                d31=float_or_nan(d31_line_edit.text()),
                d=float_or_nan(d_line_edit.text()),
                rho=float_or_nan(rho_line_edit.text()) / 1e9,
                m=float_or_nan(m_line_edit.text()),
                imax=float_or_nan(imax_line_edit.text())
            )
            self.add_new_line_model(name, new_param)

        submit_new_line_type_push_button = QPushButton("Submit")
        submit_new_line_type_push_button.pressed.connect(add_new_line_model)
        new_line_type.addWidget(submit_new_line_type_push_button)
        new_line_type.addStretch()

        self.clear_layout(self.right_sidebar_layout)
        self.right_sidebar_layout.addLayout(new_line_type)

    def control_panel_menu(self):
        # Layout for simulation control panel
        control_panel_layout = QVBoxLayout()

        nmax_hbox = QHBoxLayout()
        nmax_slider = QSlider()
        nmax_slider.setMinimum(0)
        nmax_slider.setMaximum(50)
        nmax_slider.setValue(self.max_niter)
        nmax_slider.setOrientation(Qt.Vertical)
        nmax_label = QLabel("Nmax: {:02d}".format(self.max_niter))
        nmax_slider.valueChanged.connect(lambda val: self.set_nmax(val,
                                                                   nmax_label))
        nmax_hbox.addWidget(nmax_label)
        nmax_hbox.addWidget(nmax_slider)

        control_panel_layout.addStretch()
        control_panel_layout.addLayout(nmax_hbox)
        control_panel_layout.addStretch()

        self.clear_layout(self.right_sidebar_layout)
        self.right_sidebar_layout.addLayout(control_panel_layout)

    def bus_menu(self, bus, edit_gen=False, edit_load=False):
        # Layout for general bus case
        bus_layout = QVBoxLayout()
        is_slack = (bus.bus_id == 0)
        has_load = (bus.pl != 0 or bus.ql != 0)
        has_gen = (bus.pg > 0 or bus.qg != 0)
        # Bus title
        if is_slack:
            bus_title = QLabel("Slack")
        else:
            bus_title = QLabel("Bus {}".format(bus.bus_id + 1))
        bus_title.setAlignment(Qt.AlignCenter)

        # Bus voltage
        bus_v_value = QLineEdit(safe_repr(bus.v))
        bus_v_value.setValidator(QDoubleValidator(bottom=0., top=100.))
        bus_v_value.setEnabled(edit_gen)
        # Bus angle
        bus_angle_value = QLineEdit(safe_repr(bus.delta, np.pi / 180))
        bus_angle_value.setEnabled(False)

        # FormLayout to hold bus data
        bus_data_form_layout = QFormLayout()
        # Adding bus voltage and bus angle to bus data FormLayout
        bus_data_form_layout.addRow("|V| (pu)", bus_v_value)
        bus_data_form_layout.addRow("\u03b4 (\u00B0)", bus_angle_value)

        # Label with 'Generation'
        add_generation_label = QLabel("Generation")
        add_generation_label.setAlignment(Qt.AlignCenter)

        # Line edit to Xd bus
        xd_line_edit = QLineEdit(safe_repr(bus.xd, 0.01))
        xd_line_edit.setValidator(QDoubleValidator())
        xd_line_edit.setEnabled(edit_gen)
        # Line edit to input bus Pg
        pg_input = QLineEdit(safe_repr(bus.pg, 0.01, "{:.4g}"))
        pg_input.setValidator(QDoubleValidator(bottom=0.))
        pg_input.setEnabled(edit_gen and not is_slack)
        # Line edit to input bus Qg
        qg_input = QLineEdit(safe_repr(bus.qg, 0.01, "{:.4g}"))
        qg_input.setValidator(QDoubleValidator())
        qg_input.setEnabled(False)
        # Check box for generation ground
        gen_ground = QCheckBox("\u23DA")
        gen_ground.setChecked(bus.gen_ground)
        gen_ground.setEnabled(edit_gen)

        # Button to add generation
        if edit_gen:
            def submit_gen():
                bus_v = float(bus_v_value.text())
                pg = float(pg_input.text()) / 100
                if xd_line_edit.text() == "\u221E":
                    xd = np.inf
                else:
                    xd = float(xd_line_edit.text()) / 100
                self.submit_gen(bus_v, pg, gen_ground.isChecked(), xd)

            add_generation_button = QPushButton('OK')
            add_generation_button.pressed.connect(submit_gen)
        elif is_slack:
            add_generation_button = QPushButton('EDIT')
            add_generation_button.pressed.connect(self.add_gen)
        elif has_gen:
            add_generation_button = QPushButton('-')
            add_generation_button.pressed.connect(self.remove_gen)
        else:
            add_generation_button = QPushButton('+')
            add_generation_button.pressed.connect(self.add_gen)

        # FormLayout to add generation section
        add_generation_form_layout = QFormLayout()
        # Adding Pg, Qg to add generation FormLayout
        add_generation_form_layout.addRow("x (%pu)", xd_line_edit)
        add_generation_form_layout.addRow("P<sub>G</sub> (MW)", pg_input)
        add_generation_form_layout.addRow("Q<sub>G</sub> (Mvar)", qg_input)
        add_generation_form_layout.addRow("Y", gen_ground)

        # Label with 'Load'
        add_load_label = QLabel("Load")
        add_load_label.setAlignment(Qt.AlignCenter)

        # LineEdit with Ql, Pl
        ql_input = QLineEdit(safe_repr(bus.ql, 0.01, "{:.4g}"))
        ql_input.setValidator(QDoubleValidator())
        pl_input = QLineEdit(safe_repr(bus.pl, 0.01, "{:.4g}"))
        pl_input.setValidator(QDoubleValidator())
        pl_input.setEnabled(edit_load)
        ql_input.setEnabled(edit_load)
        # Check box to load ground
        load_ground = QComboBox()
        load_ground.addItem("Y")
        load_ground.addItem("Y\u23DA")
        load_ground.addItem("\u0394")
        load_ground.setCurrentText(PY_TO_SYMBOL[bus.load_ground])
        load_ground.setEnabled(edit_load)

        # PushButton that binds to three different methods
        if edit_load:
            def submit_load():
                pl = float(pl_input.text()) / 100
                ql = float(ql_input.text()) / 100
                lg = SYMBOL_TO_PY[load_ground.currentText()]
                self.submit_load(pl, ql, lg)

            add_load_button = QPushButton('OK')
            add_load_button.pressed.connect(submit_load)
        elif has_load:
            add_load_button = QPushButton('-')
            add_load_button.pressed.connect(self.remove_load)
        else:
            add_load_button = QPushButton('+')
            add_load_button.pressed.connect(self.add_load)

        # FormLayout to add load section
        add_load_form_layout = QFormLayout()
        # Adding Pl and Ql to add load FormLayout
        add_load_form_layout.addRow("P<sub>L</sub> (MW)", pl_input)
        add_load_form_layout.addRow("Q<sub>L</sub> (Mvar)", ql_input)
        add_load_form_layout.addRow("Y", load_ground)

        remove_bus_button = QPushButton("Remove bus")
        remove_bus_button.pressed.connect(self.remove_bus)

        bus_layout.addStretch()
        bus_layout.addWidget(bus_title)
        bus_layout.addLayout(bus_data_form_layout)
        bus_layout.addWidget(add_generation_label)
        bus_layout.addWidget(add_generation_button)
        bus_layout.addLayout(add_generation_form_layout)
        bus_layout.addWidget(add_load_label)
        bus_layout.addWidget(add_load_button)
        bus_layout.addLayout(add_load_form_layout)
        bus_layout.addWidget(remove_bus_button)
        bus_layout.addStretch()

        self.clear_layout(self.left_sidebar_layout)
        self.left_sidebar_layout.addLayout(bus_layout)

    def update_layout(self):
        """Hide or show specific layouts, based on the current element or
        passed parameters by trigger methods.
        Called two times ever because self.update_values is triggered
        whenever the mouse is released
        ------------------------------------------------------------------------------------------------------
        Called by: update_values
        ------------------------------------------------------------------------------------------------------
        """

        # Even if there are two elements in the same square, only one will be identified
        # Bus has high priority
        # After, lines and trafo have equal priority
        bus = self.bus_at(self._curr_element_coord)
        curve = self.curve_at(self._curr_element_coord)
        if bus is not None:
            self.bus_menu(bus)
        elif curve is not None:
            if isinstance(curve.obj, TransmissionLine):
                self.line_menu()
            elif isinstance(curve.obj, Transformer):
                self.trafo_menu()
        else:
            self.no_menu()

    def add_line(self, curve):
        self.curves.append(curve)
        self.system.add_line(curve.obj, tuple(curve.coords))

    def add_trafo(self, curve):
        self.curves.append(curve)
        self.system.add_trafo(curve.obj, tuple(curve.coords))

    def add_bus(self):
        """
        Called by: editor.mouseDoubleClickEvent
        """
        coord = self._curr_element_coord
        is_bus = isinstance(self.editor.bus_grid[coord], Bus)
        curve = self.curve_at(self._curr_element_coord)
        if not is_bus and curve is None:
            bus = self.system.add_bus()
            self.editor.bus_grid[coord] = bus
            self.status_msg.emit("Added bus")
            self.update_values()
        else:
            self.editor.removeItem(self.editor.drawings[coord])
            self.status_msg.emit("There is an element in this position!")

    def submit_trafo(self, snom, x0, x1, primary, secondary):
        """
        Updates a trafo with the given parameters if the current element is a
        trafo or converts a line into a trafo with the inputted parameters
        Called by: trafo_submit_push_button.pressed
        """
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, TransmissionLine):
            # Transform line into a trafo
            line = curve.obj
            self.remove_line(curve)
            new_trafo = Transformer(
                orig=line.orig,
                dest=line.dest,
                snom=snom,
                jx0=x0,
                jx1=x1,
                primary=primary,
                secondary=secondary
            )
            new_curve = LineSegment(obj=new_trafo,
                                    dlines=curve.dlines,
                                    coords=curve.coords)
            for line_drawing in new_curve.dlines:
                blue_pen = QPen()
                blue_pen.setColor(Qt.red)
                blue_pen.setWidthF(2.5)
                line_drawing.setPen(blue_pen)
                self.editor.addItem(line_drawing)
            self.add_trafo(new_curve)
            self.status_msg.emit("Line -> trafo")
            self.update_values()
        elif isinstance(curve.obj, Transformer):
            # Update parameters of selected trafo
            trafo = curve.obj
            trafo.snom = snom
            trafo.jx0 = x0
            trafo.jx1 = x1
            trafo.primary = primary
            trafo.secondary = secondary
            self.status_msg.emit("Updated trafo parameters")
            self.update_values()

    def remove_curve(self, curve=None):
        if curve is None:
            curve = self.curve_at(self._curr_element_coord)
        for line_drawing in curve.dlines:
            self.editor.removeItem(line_drawing)
        self.curves.remove(curve)

    def remove_trafo(self, curve=None):
        """Remove a trafo (draw and electrical representation)
        Parameters
        ----------
        curve: curve of trafo to be removed.
            If it is None, current selected trafo in interface will be removed
        """
        if curve is None:
            curve = self.curve_at(self._curr_element_coord)
        self.remove_curve(curve)
        self.system.remove_trafo(curve.obj, tuple(curve.coords))
        self.status_msg.emit("Removed trafo")
        self.update_values()

    def remove_line(self, curve=None):
        """Remove a line (draw and electrical representation)

        Parameters
        ----------
        curve: curve of line to be removed.
            If it is None, current selected line in interface will be removed
        """
        if curve is None:
            curve = self.curve_at(self._curr_element_coord)
        self.remove_curve(curve)
        self.system.remove_line(curve.obj, tuple(curve.coords))
        self.status_msg.emit("Removed line")
        self.update_values()

    def remove_elements_linked_to(self, bus):
        """
        Called by: remove_bus

        Parameters
        ----------
        bus: Bus object
        """
        linked = []
        for curve in self.curves:
            if bus.bus_id in (curve.obj.orig.bus_id, curve.obj.dest.bus_id):
                linked.append(curve)
        for curve in linked:
            self.remove_curve(curve)

    def remove_bus(self):
        """
        Called by: remove_bus_button.pressed
        """
        coord = self._curr_element_coord
        bus = self.bus_at(coord)
        if bus:
            self.remove_elements_linked_to(bus)
            n = self.system.id2n(bus.bus_id)
            self.system.remove_bus(n)
            self.editor.removeItem(self.editor.drawings[coord])
            self.editor.drawings[coord] = 0
            self.editor.bus_grid[coord] = 0
            self.update_values()

    def add_gen(self):
        """Adds generation to the bus, make some QLineEdits activated
        Called by: add_generation_button.pressed
        """
        bus = self.bus_at(self._curr_element_coord)
        self.bus_menu(bus, edit_gen=True)
        self.status_msg.emit("Input generation data...")

    def submit_gen(self, bus_v, pg, gen_ground, xd):
        """Updates bus parameters with the user input in bus inspector
        Called by: add_generation_button.pressed
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.v = bus_v
            bus.pg = pg
            bus.gen_ground = gen_ground
            bus.xd = xd
            self.status_msg.emit("Added generation")
            self.update_values()

    def remove_gen(self):
        """
        Called by: add_generation_button.pressed
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.v = 1
            bus.pg = 0
            bus.xd = np.inf
            bus.gen_ground = False
            self.status_msg.emit("Removed generation")
            self.update_values()

    def add_load(self):
        """
        Called by: add_load_button.pressed
        """
        bus = self.bus_at(self._curr_element_coord)
        self.bus_menu(bus, edit_load=True)
        self.status_msg.emit("Input load data...")

    def submit_load(self, pl, ql, load_ground):
        """
        Called by: add_load_button.pressed
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.pl = pl
            bus.ql = ql
            bus.load_ground = load_ground
            self.status_msg.emit("Added load")
            self.update_values()

    def remove_load(self):
        """
        Called by: add_load_button.pressed
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.pl = 0
            bus.ql = 0
            bus.load_ground = EARTH
            self.status_msg.emit("Removed load")
            self.update_values()

    def update_values(self):
        """
        If line's bool remove is True, the line will be removed.
        The remove may have three causes:
        1. The line crossed with itself or with another line
        2. The line was inputted with only two points
        3. The line has not a destination bus
        """
        if self.curves:
            curr_curve = self.curves[-1]
            curr_curve.remove |= len(curr_curve.coords) <= 2
            curr_curve.remove |= curr_curve.obj.dest is None
            curr_curve.remove |= curr_curve.obj.dest == curr_curve.obj.orig
            if not self._start_line and not curr_curve.remove:
                self.system.add_line(curr_curve.obj, tuple(curr_curve.coords))
            self._start_line = True
            if curr_curve.remove:
                self.remove_curve(curr_curve)
        if self.max_niter > 0:
            self.system.update(Nmax=self.max_niter)
        self.update_layout()


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.status_bar = self.statusBar()
        screen_resolution = QDesktopWidget().availableGeometry()
        max_width = screen_resolution.width()
        max_height = screen_resolution.height()
        # Central widget
        self.main_widget = MainWidget(editor_square_length=max_width // 30)
        self.main_widget.status_msg.connect(self.status_bar.showMessage)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("Electrical Grid Analysis Tool")
        self.setGeometry(50, 50, .7 * max_width, .7 * max_height)
        self.init_ui()
        self.show()

    def init_ui(self):
        self.status_bar.showMessage("Ready")
        # Actions
        new_sys = QAction("Start new system", self)
        new_sys.setShortcut("Ctrl+N")
        new_sys.setStatusTip("Start new system (clears current one)")
        new_sys.triggered.connect(self.start_new_session)

        save_act = QAction("Save current session", self)
        save_act.setShortcut("Ctrl+S")
        save_act.setStatusTip("Save current session to a file")
        save_act.triggered.connect(self.save_session)

        load_act = QAction("Open session", self)
        load_act.setShortcut("Ctrl+O")
        load_act.setStatusTip("Open file")
        load_act.triggered.connect(self.load_session)

        report_act = QAction("Generate report", self)
        report_act.setShortcut("Ctrl+R")
        report_act.setStatusTip("Generate report")
        report_act.triggered.connect(self.report)

        add_line_act = QAction("Add line type", self)
        add_line_act.setShortcut("Ctrl+L")
        add_line_act.setStatusTip("New line model")
        add_line_act.triggered.connect(self.add_line_type)

        edit_line_act = QAction("Edit line type", self)
        edit_line_act.setStatusTip("Edit line model (not implemented)")
        edit_line_act.triggered.connect(self.edit_line_type)

        configure_simulation = QAction("Configure simulation", self)
        configure_simulation.setShortcut("Ctrl+X")
        configure_simulation.setStatusTip("Change maximum number of iterations")
        configure_simulation.triggered.connect(self.configure_simulation)

        # Menu bar
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&Session')
        file_menu.addAction(save_act)
        file_menu.addAction(load_act)
        file_menu.addAction(report_act)
        file_menu.addAction(new_sys)

        line_menu = menu_bar.addMenu('&Lines')
        line_menu.addAction(add_line_act)
        line_menu.addAction(edit_line_act)

        settings = menu_bar.addMenu('S&ettings')
        settings.addAction(configure_simulation)

    def resizeEvent(self, event):
        new_width = event.size().width()
        sidebar_width = 0.2 * new_width
        self.main_widget.left_sidebar_widget.setMaximumWidth(sidebar_width)
        self.main_widget.left_sidebar_widget.setMinimumWidth(sidebar_width)
        QMainWindow.resizeEvent(self, event)

    def configure_simulation(self):
        self.main_widget.control_panel_menu()

    def save_session(self):
        sessions_dir = getSessionsDir()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(parent=self,
                                                  caption="Save Session",
                                                  directory=sessions_dir,
                                                  filter="All Files (*)",
                                                  options=options)
        if filename:
            with open(filename, 'bw') as file:
                self.store_data(file)
                file.close()

    def load_session(self):
        sessions_dir = getSessionsDir()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(parent=self,
                                                  caption="Load Session",
                                                  directory=sessions_dir,
                                                  filter="All Files (*)",
                                                  options=options)
        if filename:
            self.start_new_session()
            with open(filename, 'br') as file:
                self.create_local_data(file)
                file.close()
            self.create_schematic(self.main_widget.editor)

    def report(self):
        sessions_dir = getSessionsDir()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        if shutil.which("latexmk") is not None:
            file_type = "PDF Files (*.pdf)"
        else:
            file_type = "Data Files (*.dat)"
        filename, _ = QFileDialog.getSaveFileName(parent=self,
                                                  caption="Save Report",
                                                  directory=sessions_dir,
                                                  filter=file_type,
                                                  options=options)
        if filename:
            create_report(self.main_widget.system, self.main_widget.curves,
                          self.main_widget.editor.bus_grid, filename)

    def add_line_type(self):
        self.main_widget.new_line_model_menu()
        self.status_bar.showMessage("Adding new line model")

    def edit_line_type(self):
        self.status_bar.showMessage("Editing line types is currently not implemented!")
        raise NotImplementedError

    def start_new_session(self):
        self.clear_interface()
        self.reset_system_state_variables()
        self.main_widget.update_values()

    def clear_interface(self):
        to_remove = len(self.main_widget.curves)
        for i in range(to_remove):
            self.main_widget.remove_curve(self.main_widget.curves[0])
        editor = self.main_widget.editor
        size = editor.size
        for i in range(size):
            for j in range(size):
                if isinstance(editor.bus_grid[i, j], Bus):
                    editor.removeItem(editor.drawings[i, j])

    def reset_system_state_variables(self):
        size = self.main_widget.editor.size
        self.main_widget.system = PowerSystem()
        self.main_widget.curves = []
        self.main_widget.editor.bus_grid = np.zeros((size, size), object)
        self.main_widget.editor.drawings = np.zeros((size, size), object)

    def create_local_data(self, file):
        db = pickle.load(file)
        self.main_widget.system = db['SYSTEM']
        self.main_widget.curves = db['CURVES']
        self.main_widget.line_types = db['LINE_TYPES']
        self.main_widget.editor.bus_grid = db['GRID']

    def store_data(self, file):
        filtered_curves = []
        for curve in self.main_widget.curves:
            filtered_curves.append(LineSegment(obj=curve.obj,
                                               coords=curve.coords,
                                               dlines=[]))
        db = {'SYSTEM': self.main_widget.system,
              'CURVES': filtered_curves,
              'LINE_TYPES': self.main_widget.line_types,
              'GRID': self.main_widget.editor.bus_grid}
        pickle.dump(db, file)
        return db

    def create_schematic(self, editor):
        square_length = editor.square_length
        for i in range(editor.size):
            for j in range(editor.size):
                if isinstance(editor.bus_grid[i, j], Bus):
                    point = (square_length * (j + .5),
                             square_length * (i + .5))
                    bus = editor.draw_bus(point)
                    editor.drawings[i, j] = bus
        for curve in self.main_widget.curves:
            for pair in interface_coordpairs(curve.coords, square_length):
                if isinstance(curve.obj, TransmissionLine):
                    dline = editor.draw_line(pair[0], pair[1], color='b')
                else:
                    dline = editor.draw_line(pair[0], pair[1], color='r')
                curve.dlines.append(dline)


def main():
    app = QApplication(sys.argv)
    _ = Window()
    sys.exit(app.exec_())
