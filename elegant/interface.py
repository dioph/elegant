import pickle
import shutil

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .core import *
from .report import create_report
from .utils import *

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
        if self.scene().selectorHistory.dsquare_obj is not None:
            self.scene().removeItem(self.scene().selectorHistory.dsquare_obj)
            self.scene().selectorHistory.dsquare_obj = None


class Editor(QGraphicsScene):
    def __init__(self, size=20, length=50):
        super(Editor, self).__init__()
        self.size = size
        self.View = ScrollView(self)

        # System state variables
        self.drawings = np.zeros((self.size, self.size), object)
        self.bus_grid = np.zeros((self.size, self.size), object)
        self.square_length = length
        self.move_history = HistoryData()
        self.block = Block()
        self.selectorHistory = HistoryData()
        self.selectorHistory.__setattr__('dsquare_obj', None)

        self.pointer_signal = GenericSignal()
        self.method_signal = GenericSignal()
        self.data_signal = GenericSignal()

        # Visible portion of Scene to View
        self.circle_radius = length / 2
        self.setSceneRect(0,
                          0,
                          self.square_length * self.size,
                          self.square_length * self.size)
        self.coord_grid = self.get_coord_grid()
        self.draw_grid()
        self.setSceneRect(self.square_length * -2,
                          self.square_length * -2,
                          self.square_length * (self.size + 4),
                          self.square_length * (self.size + 4))

    @staticmethod
    def distance(interface_point, point):
        """
        Parameters
        ----------
        interface_point: center of bump box from interface points
        point: clicked point by user

        Returns
        -------
        : distance between point and interface_point
        """
        return np.hypot(interface_point[0] - point.x(), interface_point[1] - point.y())

    def ij_from_QPoint(self, central_point):
        """
        Parameters
        ----------
        central_point: coordinates of quantized point from interface

        Returns
        -------
        : index codes for point, given its quantized coordinates
        """
        i = int((central_point.y() - self.square_length / 2) / self.square_length)
        j = int((central_point.x() - self.square_length / 2) / self.square_length)
        return i, j

    def QPoint_from_ij(self, i, j):
        for central_point in self.coord_grid.flatten():
            if (i, j) == self.ij_from_QPoint(central_point):
                return central_point

    def draw_line(self, coordinates, color='b'):
        """
        Parameters
        ----------
        coordinates: coordinates that guide line drawing
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
        line = self.addLine(coordinates[0, 0], coordinates[0, 1], coordinates[1, 0], coordinates[1, 1], pen)
        return line

    def draw_square(self, coordinates):
        """
        Parameters
        ----------
        coordinates: coordinates that guide square drawing

        Returns
        -------
        QRect: drawn square (PyQt5 object)
        """
        pen = QPen(Qt.yellow)
        brush = QBrush(Qt.yellow, Qt.Dense7Pattern)
        x, y = coordinates
        rect = self.addRect(x, y, self.square_length, self.square_length, pen, brush)
        return rect

    def draw_bus(self, coordinates):
        c = np.array(coordinates) - self.square_length / 4
        pen = QPen(Qt.black)
        brush = QBrush(Qt.SolidPattern)
        ellipse = self.addEllipse(*c, self.square_length / 2, self.square_length / 2, pen, brush)
        return ellipse

    def get_central_point(self, event):
        coordinates = event.scenePos().x(), event.scenePos().y()
        for central_point in self.coord_grid.flatten():
            if self.distance(coordinates, central_point) <= self.circle_radius:
                i, j = self.ij_from_QPoint(central_point)
                return central_point, i, j

    def mouseReleaseEvent(self, event):
        self.move_history.reset()
        self.block.start = True
        self.block.end = False
        self.method_signal.emit_sig(3)

    def mouseDoubleClickEvent(self, event):
        if self.get_central_point(event):
            central_point, i, j = self.get_central_point(event)
            circle = self.draw_bus((central_point.x(), central_point.y()))
            self.drawings[i, j] = circle
            self.pointer_signal.emit_sig((i, j))
            self.method_signal.emit_sig(0)

    def redraw_cursor(self, x, y):
        if self.selectorHistory.dsquare_obj is not None:
            self.removeItem(self.selectorHistory.dsquare_obj)
        self.selectorHistory.set_current(x - self.square_length / 2,
                                         y - self.square_length / 2)
        self.selectorHistory.dsquare_obj = self.draw_square(self.selectorHistory.current)

    def mousePressEvent(self, event):
        if self.get_central_point(event):
            central_point, i, j = self.get_central_point(event)
            x, y = central_point.x(), central_point.y()
            self.redraw_cursor(x, y)
            self.pointer_signal.emit_sig((i, j))
            self.method_signal.emit_sig(4)
            self.method_signal.emit_sig(2)

    @property
    def is_drawing_blocked(self):
        return self.block.start or self.block.end

    def draw_line_suite(self, i, j):
        coordinates = np.atleast_2d(np.array([self.move_history.last, self.move_history.current]))
        line = self.draw_line(coordinates, color='b')
        self.move_history.reset()
        self.pointer_signal.emit_sig((i, j))
        self.data_signal.emit_sig(line)
        self.method_signal.emit_sig(1)

    def mouseMoveEvent(self, event):
        if self.get_central_point(event):
            central_point, i, j = self.get_central_point(event)
            if central_point is not None:
                x, y = central_point.x(), central_point.y()
                self.redraw_cursor(x, y)
                if self.move_history.is_empty:
                    self.move_history.set_last(x, y)
                    if isinstance(self.bus_grid[i, j], Bus):
                        self.block.start = False
                if self.move_history.is_last_different_from(x, y):
                    self.move_history.set_current(x, y)
                if self.move_history.allows_drawing and not self.is_drawing_blocked:
                    self.draw_line_suite(i, j)
                    if isinstance(self.bus_grid[i, j], Bus):
                        self.block.end = True

    def get_coord_grid(self):
        """
        Returns
        -------
        coord_grid: numpy array that holds PyQt QPoint objects with quantized interface coordinates
        """
        coord_grid = np.zeros((self.size, self.size), tuple)
        width, height = self.width(), self.height()
        for i in range(self.size):
            for j in range(self.size):
                coord_grid[i, j] = QPoint(int(width / (2 * self.size) + i * width / self.size),
                                          int(height / (2 * self.size) + j * height / self.size))
        return coord_grid

    def draw_grid(self):
        """Display the quantized interface guidelines"""
        width, height = self.width(), self.height()
        spacing_x, spacing_y = width / self.size, height / self.size
        quantized_x, quantized_y = np.arange(0, width, spacing_x), np.arange(0, height, spacing_y)
        pen = QPen()
        pen.setColor(Qt.lightGray)
        pen.setStyle(Qt.DashDotDotLine)
        for k in range(self.size):
            # Horizontal lines
            self.addLine(0.0, quantized_y[k], width, quantized_y[k], pen)
            # Vertical lines
            self.addLine(quantized_x[k], 0.0, quantized_x[k], height, pen)
        self.addLine(0.0, self.height(), width, self.height(), pen)
        self.addLine(self.width(), 0.0, self.width(), height, pen)


class MainWidget(QWidget):
    def __init__(self, parent=None):
        # General initializations
        super(MainWidget, self).__init__(parent)
        self.system = PowerSystem()
        self.line_types = {"Default": TransmissionLine(orig=None, dest=None)}
        self.curves = []
        self.max_niter = 20
        self.sidebar_width = 200

        self.editor = Editor()

        # self.View = QGraphicsView(self.Scene)
        self.view = self.editor.View
        self.editor_layout = QHBoxLayout()  # Layout for SchemeInput
        self.editor_layout.addWidget(self.view)
        self._curr_element_coord = None  # Coordinates to current object being manipuled
        self._start_line = True
        self._line_origin = None
        self._temp = None
        self.status_msg = GenericSignal()
        self.__calls = {0: self.add_bus,
                        1: self.add_segment,
                        2: self.update_layout,
                        3: self.update_values,
                        4: self.store_line_origin}
        self.editor.pointer_signal.signal.connect(self.set_current_coord)
        self.editor.data_signal.signal.connect(self.set_temp)
        self.editor.method_signal.signal.connect(self.methods_trigger)

        # Inspectors
        self.inspector_layout = QVBoxLayout()

        # Layout for general bus case
        self.bus_layout = QVBoxLayout()

        # Bus title
        self.bus_title = QLabel("Bus title")
        self.bus_title.setAlignment(Qt.AlignCenter)
        self.bus_title.setMinimumWidth(self.sidebar_width)
        self.bus_title.setMaximumWidth(self.sidebar_width)

        # Bus voltage
        self.bus_v_value = QLineEdit("0.0")
        self.bus_v_value.setEnabled(False)
        self.bus_v_value.setValidator(QDoubleValidator(bottom=0., top=100.))

        # Bus angle
        self.bus_angle_value = QLineEdit("0.0")
        self.bus_angle_value.setEnabled(False)

        # FormLayout to hold bus data
        self.bus_data_form_layout = QFormLayout()

        # Adding bus voltage and bus angle to bus data FormLayout
        self.bus_data_form_layout.addRow("|V| (pu)", self.bus_v_value)
        self.bus_data_form_layout.addRow("\u03b4 (\u00B0)", self.bus_angle_value)

        # Label with 'Generation'
        self.add_generation_label = QLabel("Generation")
        self.add_generation_label.setAlignment(Qt.AlignCenter)

        # Button to add generation
        self.add_generation_button = QPushButton('+')
        self.add_generation_button.pressed.connect(self.add_gen)  # Bind button to make input editable

        # FormLayout to add generation section
        self.add_generation_form_layout = QFormLayout()
        self.add_load_form_layout = QFormLayout()

        # Line edit to Xd bus
        self.xd_line_edit = QLineEdit("\u221E")
        self.xd_line_edit.setValidator(QDoubleValidator())
        self.xd_line_edit.setEnabled(False)

        # Line edit to input bus Pg
        self.pg_input = QLineEdit("0.0")
        self.pg_input.setValidator(QDoubleValidator(bottom=0.))
        self.pg_input.setEnabled(False)

        # Line edit to input bus Qg
        self.qg_input = QLineEdit("0.0")
        self.qg_input.setValidator(QDoubleValidator())
        self.qg_input.setEnabled(False)

        # Check box for generation ground
        self.gen_ground = QCheckBox("\u23DA")
        self.gen_ground.setEnabled(False)

        # Adding Pg, Qg to add generation FormLayout
        self.add_generation_form_layout.addRow("x (%pu)", self.xd_line_edit)
        self.add_generation_form_layout.addRow("P<sub>G</sub> (MW)", self.pg_input)
        self.add_generation_form_layout.addRow("Q<sub>G</sub> (Mvar)", self.qg_input)
        self.add_generation_form_layout.addRow("Y", self.gen_ground)

        # Label with 'Load'
        self.add_load_label = QLabel("Load")
        self.add_load_label.setAlignment(Qt.AlignCenter)

        # PushButton that binds to three different methods
        self.add_load_button = QPushButton('+')
        self.add_load_button.pressed.connect(self.add_load)

        # LineEdit with Ql, Pl
        self.ql_input = QLineEdit("0.0")
        self.ql_input.setValidator(QDoubleValidator())
        self.pl_input = QLineEdit("0.0")
        self.pl_input.setValidator(QDoubleValidator())
        self.pl_input.setEnabled(False)
        self.ql_input.setEnabled(False)

        # Check box to load ground
        # self.LoadGround = QCheckBox("\u23DA")
        self.load_ground = QComboBox()
        self.load_ground.addItem("Y")
        self.load_ground.addItem("Y\u23DA")
        self.load_ground.addItem("\u0394")
        self.load_ground.setEnabled(False)

        # Adding Pl and Ql to add load FormLayout
        self.add_load_form_layout.addRow("P<sub>L</sub> (MW)", self.pl_input)
        self.add_load_form_layout.addRow("Q<sub>L</sub> (Mvar)", self.ql_input)
        self.add_load_form_layout.addRow("Y", self.load_ground)

        self.remove_bus_button = QPushButton('Remove bus')
        self.remove_bus_button.pressed.connect(self.remove_bus)

        self.bus_layout.addWidget(self.bus_title)
        self.bus_layout.addLayout(self.bus_data_form_layout)
        self.bus_layout.addWidget(self.add_generation_label)
        self.bus_layout.addWidget(self.add_generation_button)
        self.bus_layout.addLayout(self.add_generation_form_layout)
        self.bus_layout.addWidget(self.add_load_label)
        self.bus_layout.addWidget(self.add_load_button)
        self.bus_layout.addLayout(self.add_load_form_layout)
        self.bus_layout.addWidget(self.remove_bus_button)

        # Layout for input new type of line
        self.new_line_type = QVBoxLayout()
        self.new_line_type_form_layout = QFormLayout()

        self.model_name = QLineEdit()
        self.model_name.setValidator(QRegExpValidator(QRegExp("[A-Za-z]*")))
        self.rho_line_edit = QLineEdit()
        self.rho_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.r_line_edit = QLineEdit()
        self.r_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d12_line_edit = QLineEdit()
        self.d12_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d23_line_edit = QLineEdit()
        self.d23_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d31_line_edit = QLineEdit()
        self.d31_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d_line_edit = QLineEdit()
        self.d_line_edit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.m_line_edit = QLineEdit()
        self.m_line_edit.setValidator(QIntValidator(bottom=1, top=4))
        self.imax_line_edit = QLineEdit()
        self.imax_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.new_line_type_form_layout.addRow("Name", self.model_name)
        self.new_line_type_form_layout.addRow("\u03C1 (n\u03A9m)", self.rho_line_edit)
        self.new_line_type_form_layout.addRow("r (mm)", self.r_line_edit)
        self.new_line_type_form_layout.addRow("d12 (m)", self.d12_line_edit)
        self.new_line_type_form_layout.addRow("d23 (m)", self.d23_line_edit)
        self.new_line_type_form_layout.addRow("d31 (m)", self.d31_line_edit)
        self.new_line_type_form_layout.addRow("d (m)", self.d_line_edit)
        self.new_line_type_form_layout.addRow("m", self.m_line_edit)
        self.new_line_type_form_layout.addRow("Imax (A)", self.imax_line_edit)

        self.new_line_type.addStretch()
        self.new_line_type.addLayout(self.new_line_type_form_layout)
        self.submit_new_line_type_push_button = QPushButton("Submit")
        self.submit_new_line_type_push_button.setMinimumWidth(self.sidebar_width)
        self.submit_new_line_type_push_button.setMaximumWidth(self.sidebar_width)
        self.submit_new_line_type_push_button.pressed.connect(self.add_new_line_model)
        self.new_line_type.addWidget(self.submit_new_line_type_push_button)
        self.new_line_type.addStretch()

        # Layout for simulation control panel
        self.control_panel_layout = QVBoxLayout()

        self.nmax_hbox = QHBoxLayout()
        self.nmax_slider = QSlider()
        self.nmax_slider.setMinimum(0)
        self.nmax_slider.setMaximum(50)
        self.nmax_slider.setOrientation(Qt.Vertical)
        self.nmax_label = QLabel("Nmax: {:02d}".format(self.max_niter))
        self.nmax_slider.valueChanged.connect(self.set_nmax)
        self.nmax_hbox.addWidget(self.nmax_label)
        self.nmax_hbox.addWidget(self.nmax_slider)

        self.control_panel_layout.addStretch()
        self.control_panel_layout.addLayout(self.nmax_hbox)
        self.control_panel_layout.addStretch()

        # General Layout for TL case
        self.line_or_trafo_layout = QVBoxLayout()

        self.choose_line = QRadioButton("TL")
        self.choose_trafo = QRadioButton("TRAFO")
        self.choose_line.toggled.connect(self.toggle_line_trafo)
        self.choose_trafo.toggled.connect(self.toggle_line_trafo)

        self.choose_line_or_trafo = QHBoxLayout()
        self.choose_line_or_trafo.addWidget(QLabel("TL/TRAFO:"))
        self.choose_line_or_trafo.addWidget(self.choose_line)
        self.choose_line_or_trafo.addWidget(self.choose_trafo)

        self.chosen_line_form_layout = QFormLayout()

        self.choose_line_model = QComboBox()
        self.choose_line_model.addItem("No model")

        self.ell_line_edit = QLineEdit()
        self.ell_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.vbase_line_edit = QLineEdit()
        self.vbase_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.tl_r_line_edit = QLineEdit()
        self.tl_r_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.tl_x_line_edit = QLineEdit()
        self.tl_x_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.tl_b_line_edit = QLineEdit()
        self.tl_b_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.tl_submit_by_impedance_button = QPushButton("Submit by impedance")
        self.tl_submit_by_impedance_button.setMinimumWidth(self.sidebar_width)
        self.tl_submit_by_impedance_button.setMaximumWidth(self.sidebar_width)
        self.tl_submit_by_impedance_button.pressed.connect(lambda: self.submit_line('impedance'))

        self.tl_submit_by_model_button = QPushButton("Submit by model")
        self.tl_submit_by_model_button.pressed.connect(lambda: self.submit_line('parameters'))
        self.tl_submit_by_model_button.setMinimumWidth(self.sidebar_width)
        self.tl_submit_by_model_button.setMaximumWidth(self.sidebar_width)

        self.chosen_line_form_layout.addRow("Model", self.choose_line_model)
        self.chosen_line_form_layout.addRow("\u2113 (km)", self.ell_line_edit)
        self.chosen_line_form_layout.addRow("Vbase (kV)", self.vbase_line_edit)
        self.chosen_line_form_layout.addRow("R (%pu)", self.tl_r_line_edit)
        self.chosen_line_form_layout.addRow("X<sub>L</sub> (%pu)", self.tl_x_line_edit)
        self.chosen_line_form_layout.addRow("B<sub>C</sub> (%pu)", self.tl_b_line_edit)

        self.remove_tl_push_button = QPushButton('Remove TL')
        self.remove_tl_push_button.setMinimumWidth(self.sidebar_width)
        self.remove_tl_push_button.setMaximumWidth(self.sidebar_width)
        self.remove_tl_push_button.pressed.connect(self.remove_line)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.remove_tl_push_button.pressed.connect(self.update_layout)

        self.chosen_trafo_form_layout = QFormLayout()
        self.snom_trafo_line_edit = QLineEdit()
        self.snom_trafo_line_edit.setValidator(QDoubleValidator(bottom=0.))
        self.x_zero_seq_trafo_line_edit = QLineEdit()
        self.x_zero_seq_trafo_line_edit.setValidator(QDoubleValidator(bottom=0.))
        self.x_pos_seq_trafo_line_edit = QLineEdit()
        self.x_pos_seq_trafo_line_edit.setValidator(QDoubleValidator(bottom=0.))

        self.trafo_primary = QComboBox()
        self.trafo_primary.addItem('Y')
        self.trafo_primary.addItem('Y\u23DA')
        self.trafo_primary.addItem('\u0394')
        self.trafo_secondary = QComboBox()
        self.trafo_secondary.addItem('Y')
        self.trafo_secondary.addItem('Y\u23DA')
        self.trafo_secondary.addItem('\u0394')

        self.trafo_submit_push_button = QPushButton('Submit trafo')
        self.trafo_submit_push_button.pressed.connect(self.submit_trafo)
        self.trafo_submit_push_button.setMinimumWidth(self.sidebar_width)
        self.trafo_submit_push_button.setMaximumWidth(self.sidebar_width)

        self.remove_trafo_push_button = QPushButton('Remove trafo')
        self.remove_trafo_push_button.pressed.connect(self.remove_trafo)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.remove_trafo_push_button.pressed.connect(self.update_layout)
        self.remove_trafo_push_button.setMinimumWidth(self.sidebar_width)
        self.remove_trafo_push_button.setMaximumWidth(self.sidebar_width)

        self.chosen_trafo_form_layout.addRow("Snom (MVA)", self.snom_trafo_line_edit)
        self.chosen_trafo_form_layout.addRow("x+ (%pu)", self.x_pos_seq_trafo_line_edit)
        self.chosen_trafo_form_layout.addRow("x0 (%pu)", self.x_zero_seq_trafo_line_edit)
        self.chosen_trafo_form_layout.addRow("Prim.", self.trafo_primary)
        self.chosen_trafo_form_layout.addRow("Sec.", self.trafo_secondary)

        self.line_or_trafo_layout.addLayout(self.choose_line_or_trafo)
        self.line_or_trafo_layout.addLayout(self.chosen_line_form_layout)
        self.line_or_trafo_layout.addLayout(self.chosen_trafo_form_layout)

        # Submit and remove buttons for line
        self.line_or_trafo_layout.addWidget(self.tl_submit_by_model_button)
        self.line_or_trafo_layout.addWidget(self.tl_submit_by_impedance_button)
        self.line_or_trafo_layout.addWidget(self.remove_tl_push_button)

        # Buttons submit and remove button for trafo
        self.line_or_trafo_layout.addWidget(self.trafo_submit_push_button)
        self.line_or_trafo_layout.addWidget(self.remove_trafo_push_button)

        # Layout that holds bus inspector and Stretches
        self.sidebar_layout = QVBoxLayout()
        self.inspector_layout.addStretch()
        self.inspector_layout.addLayout(self.bus_layout)
        self.inspector_layout.addLayout(self.line_or_trafo_layout)
        self.inspector_layout.addStretch()
        self.sidebar_layout.addLayout(self.inspector_layout)

        # Toplayout
        self.top_layout = QHBoxLayout()
        self.spacer = QSpacerItem(self.sidebar_width, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.top_layout.addItem(self.spacer)
        self.top_layout.addLayout(self.sidebar_layout)
        self.top_layout.addLayout(self.editor_layout)
        self.top_layout.addLayout(self.new_line_type)
        self.top_layout.addLayout(self.control_panel_layout)
        self.setLayout(self.top_layout)

        # All layouts hidden at first moment
        self.clear_layout(self.bus_layout, True)
        self.clear_layout(self.line_or_trafo_layout, True)
        self.clear_layout(self.new_line_type, True)
        self.clear_layout(self.control_panel_layout, True)
        self.show_spacer()

    def methods_trigger(self, args):
        """Trigger methods defined in __calls"""
        self.__calls[args]()

    def set_current_coord(self, args):
        """Define coordinates pointing to current selected object in interface"""
        self._curr_element_coord = args

    def hide_spacer(self):
        self.spacer.changeSize(0, 0)

    def show_spacer(self):
        self.spacer.changeSize(self.sidebar_width, 0)

    def set_temp(self, args):
        """This method stores the first line in line element drawing during line inputting.
        Its existence is justified by the first square limitation in MouseMoveEvent
        """
        self._temp = args

    def store_line_origin(self):
        if self._start_line:
            self._line_origin = self._curr_element_coord

    def clear_layout(self, layout, visible):
        """Hide completely any layout containing widgets or/and other layouts"""
        widgets = list(layout.itemAt(i).widget() for i in range(layout.count())
                       if not isinstance(layout.itemAt(i), QLayout))
        widgets = list(filter(lambda x: x is not None, widgets))
        for w in widgets:
            w.setHidden(visible)
        layouts = list(layout.itemAt(i).layout() for i in range(layout.count())
                       if isinstance(layout.itemAt(i), QLayout))
        for child_layout in layouts:
            self.clear_layout(child_layout, visible)

    def update_nmax_label(self, nmax):
        self.nmax_label.setText("Nmax: {:02d}".format(nmax))

    def update_nmax_slider(self, nmax):
        self.nmax_slider.setEnabled(True)
        self.nmax_slider.setValue(nmax)

    def set_nmax(self, nmax):
        self.max_niter = nmax
        self.update_nmax_label(self.max_niter)

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
        self.status_msg.emit_sig("Adding line...")

    def find_line_model_from_object(self, line):
        """Return the name of parameters set of a existent line or
        return None if the line has been set by impedance and admittance
        """
        for line_name, line_model in self.line_types.items():
            if line_model.param == line.param:
                return line_name
        return "No model"

    def find_line_model_from_text(self):
        """Find parameters set based on current selected line or trafo inspector combo box
        If the line was set with impedance/admittance, return 'None'
        """
        set_name = self.choose_line_model.currentText()
        for line_name, line_model in self.line_types.items():
            if set_name == line_name:
                return line_model
        return None

    def add_new_line_model(self):
        """Add a new type of line, if given parameters has passed in all the tests
        Called by: SubmitNewLineTypePushButton.pressed"""
        name = self.model_name.text()

        def float_or_nan(s):
            return np.nan if s == '' else float(s)
        new_param = dict(
            r=float_or_nan(self.r_line_edit.text()) / 1e3,
            d12=float_or_nan(self.d12_line_edit.text()),
            d23=float_or_nan(self.d23_line_edit.text()),
            d31=float_or_nan(self.d31_line_edit.text()),
            d=float_or_nan(self.d_line_edit.text()),
            rho=float_or_nan(self.rho_line_edit.text()) / 1e9,
            m=float_or_nan(self.m_line_edit.text()),
            imax=float_or_nan(self.imax_line_edit.text())
        )
        line = TransmissionLine(orig=None, dest=None)
        line.__dict__.update(new_param)
        if name in self.line_types.keys():
            self.status_msg.emit_sig('Duplicated name. Insert another valid name')
            return
        if any(np.isnan(list(new_param.values()))):
            self.status_msg.emit_sig('Undefined parameter. Fill all parameters')
            return
        if any(map(lambda x: line.param == x.param, self.line_types.values())):
            self.status_msg.emit_sig('A similar model was identified. The model has not been stored')
            return
        self.line_types[name] = line
        self.status_msg.emit_sig('The model has been stored')

    @staticmethod
    def submit_line_by_model(line, param_values, ell, vbase):
        """Update a line with parameters

        Parameters
        ----------
        line: TL object to be updated
        param_values: TL object with data to update line
        ell: line length (m)
        vbase: voltage base (V)
        """
        line.Z, line.Y = None, None
        line.__dict__.update(param_values.param)
        line.vbase = vbase
        line.ell = ell

    @staticmethod
    def submit_line_by_impedance(line, Z, Y, ell, vbase):
        """Update a line with impedance/admittance

        Parameters
        ----------
        line: TL object to be updated
        Z: impedance (ohm)
        Y: admittance (mho)
        ell: line length (m)
        vbase: voltage base (V)
        """
        zbase = vbase ** 2 / 1e8
        line.Z, line.Y = Z * zbase, Y / zbase
        line.ell = ell
        line.vbase = vbase
        line.m = 0

    def update_line_model_options(self):
        """Add the name of a new parameter set to QComboBox choose model,
           if the Combo has not the model yet
        -----------------------------------------------------------------
        """
        for line_name in self.line_types.keys():
            if self.choose_line_model.isVisible() and self.choose_line_model.findText(line_name) < 0:
                self.choose_line_model.addItem(line_name)

    def toggle_line_trafo(self):
        """Show line or trafo options in adding line/trafo section"""
        if not self.choose_line.isHidden() and not self.choose_trafo.isHidden():
            if self.choose_line.isChecked():
                # Line
                self.clear_layout(self.chosen_line_form_layout, False)
                self.clear_layout(self.chosen_trafo_form_layout, True)
                self.remove_tl_push_button.setHidden(False)
                self.tl_submit_by_impedance_button.setHidden(False)
                self.tl_submit_by_model_button.setHidden(False)
                self.trafo_submit_push_button.setHidden(True)
                self.remove_trafo_push_button.setHidden(True)
            elif self.choose_trafo.isChecked():
                # Trafo
                self.clear_layout(self.chosen_line_form_layout, True)
                self.clear_layout(self.chosen_trafo_form_layout, False)
                self.remove_tl_push_button.setHidden(True)
                self.tl_submit_by_impedance_button.setHidden(True)
                self.tl_submit_by_model_button.setHidden(True)
                self.trafo_submit_push_button.setHidden(False)
                self.remove_trafo_push_button.setHidden(False)

    def trafo_menu(self):
        """Update trafo inspector
        Calls
        -----
        LayoutManager, trafoProcessing
        """
        curve = self.curve_at(self._curr_element_coord)
        if curve is not None:
            trafo = curve.obj
            self.snom_trafo_line_edit.setText('{:.3g}'.format(trafo.snom / 1e6))
            self.x_zero_seq_trafo_line_edit.setText('{:.3g}'.format(trafo.jx0 * 100))
            self.x_pos_seq_trafo_line_edit.setText('{:.3g}'.format(trafo.jx1 * 100))
            self.trafo_primary.setCurrentText(PY_TO_SYMBOL[trafo.primary])
            self.trafo_secondary.setCurrentText(PY_TO_SYMBOL[trafo.secondary])
        else:
            self.snom_trafo_line_edit.setText('100')
            self.x_zero_seq_trafo_line_edit.setText('0.0')
            self.x_pos_seq_trafo_line_edit.setText('0.0')
            self.trafo_primary.setCurrentText(PY_TO_SYMBOL[1])
            self.trafo_secondary.setCurrentText(PY_TO_SYMBOL[1])

    def line_menu(self):
        """Updates the line inspector
        Calls
        -----
        LayoutManager, lineProcessing
        """
        curve = self.curve_at(self._curr_element_coord)
        line = curve.obj
        line_model = self.find_line_model_from_object(line)
        self.ell_line_edit.setText('{:.03g}'.format(line.ell / 1e3))
        self.vbase_line_edit.setText('{:.03g}'.format(line.vbase / 1e3))
        self.tl_r_line_edit.setText('{number.real:.04f}'.format(number=line.Zpu * 100))
        self.tl_x_line_edit.setText('{number.imag:.04f}'.format(number=line.Zpu * 100))
        self.tl_b_line_edit.setText('{number.imag:.04f}'.format(number=line.Ypu * 100))
        self.choose_line_model.setCurrentText(line_model)

    def bus_menu(self, bus):
        """Updates the bus inspector with bus data if bus exists or
        shows that there's no bus (only after bus exclusion)
        Called by: LayoutManager, remove_gen, remove_load

        Parameters
        ----------
        bus: Bus object whose data will be displayed
        """
        to_be_disabled = [self.pg_input,
                          self.pl_input,
                          self.ql_input,
                          self.bus_v_value,
                          self.xd_line_edit,
                          self.load_ground,
                          self.gen_ground]
        for item in to_be_disabled:
            item.setDisabled(True)
        if bus:
            if bus.bus_id == 0:
                self.bus_title.setText("Slack")
            else:
                self.bus_title.setText("Bus {}".format(bus.bus_id + 1))
            if bus.pl > 0 or bus.ql > 0:
                self.add_load_button.setText('-')
                self.add_load_button.disconnect()
                self.add_load_button.pressed.connect(self.remove_load)
                self.load_ground.setCurrentText(PY_TO_SYMBOL[bus.load_ground])
            else:
                self.add_load_button.setText('+')
                self.add_load_button.disconnect()
                self.add_load_button.pressed.connect(self.add_load)
                self.load_ground.setCurrentText(PY_TO_SYMBOL[EARTH])
            if (bus.pg > 0 or bus.qg > 0) and bus.bus_id > 0:
                self.add_generation_button.setText('-')
                self.add_generation_button.disconnect()
                self.add_generation_button.pressed.connect(self.remove_gen)
            elif bus.bus_id == 0:
                self.add_generation_button.setText('EDIT')
                self.add_generation_button.disconnect()
                self.add_generation_button.pressed.connect(self.add_gen)
            else:
                self.add_generation_button.setText('+')
                self.add_generation_button.disconnect()
                self.add_generation_button.pressed.connect(self.add_gen)
            self.bus_v_value.setText("{:.3g}".format(bus.v))
            self.bus_angle_value.setText("{:.3g}".format(bus.delta * 180 / np.pi))
            self.qg_input.setText("{:.4g}".format(bus.qg * 100))
            self.pg_input.setText("{:.4g}".format(bus.pg * 100))
            self.ql_input.setText("{:.4g}".format(bus.ql * 100))
            self.pl_input.setText("{:.4g}".format(bus.pl * 100))
            self.xd_line_edit.setText("{:.3g}".format(bus.xd))
            self.gen_ground.setChecked(bus.gen_ground)

        if bus.xd == np.inf:
            self.xd_line_edit.setText("\u221E")
        else:
            self.xd_line_edit.setText("{:.3g}".format(bus.xd * 100))

    def update_layout(self):
        """Hide or show specific layouts, based on the current element or
        passed parameters by trigger methods.
        Called two times ever because self.doAfterMouseRelease is triggered
        whenever the mouse is released
        ------------------------------------------------------------------------------------------------------
        Called by: doAfterMouseRelease
        ------------------------------------------------------------------------------------------------------
        """

        # Even if there are two elements in the same square, only one will be identified
        # Bus has high priority
        # After, lines and trafo have equal priority
        bus = self.bus_at(self._curr_element_coord)
        curve = self.curve_at(self._curr_element_coord)
        if bus is not None:
            # Show bus inspect
            self.hide_spacer()
            self.clear_layout(self.new_line_type, True)
            self.clear_layout(self.line_or_trafo_layout, True)
            self.clear_layout(self.control_panel_layout, True)
            self.clear_layout(self.bus_layout, False)
            self.bus_menu(bus)
        elif curve is not None:
            if isinstance(curve.obj, TransmissionLine):
                # Show line inspect
                self.hide_spacer()
                self.clear_layout(self.new_line_type, True)
                self.clear_layout(self.bus_layout, True)
                self.clear_layout(self.line_or_trafo_layout, False)
                self.choose_line.setChecked(True)
                self.clear_layout(self.chosen_trafo_form_layout, True)
                self.clear_layout(self.chosen_line_form_layout, False)
                self.trafo_submit_push_button.setHidden(True)
                self.remove_trafo_push_button.setHidden(True)
                self.clear_layout(self.control_panel_layout, True)
                self.remove_tl_push_button.setHidden(False)
                self.update_line_model_options()
                self.line_menu()
            elif isinstance(curve.obj, Transformer):
                # Show trafo inspect
                self.clear_layout(self.new_line_type, True)
                self.hide_spacer()
                self.clear_layout(self.bus_layout, True)
                self.clear_layout(self.line_or_trafo_layout, False)
                self.choose_trafo.setChecked(True)
                self.clear_layout(self.chosen_trafo_form_layout, False)
                self.clear_layout(self.chosen_line_form_layout, True)
                self.trafo_submit_push_button.setHidden(False)
                self.remove_trafo_push_button.setHidden(False)
                self.remove_tl_push_button.setHidden(True)
                self.tl_submit_by_model_button.setHidden(True)
                self.tl_submit_by_impedance_button.setHidden(True)
                self.clear_layout(self.control_panel_layout, True)
                self.trafo_menu()
        else:
            # No element case
            self.clear_layout(self.bus_layout, True)
            self.clear_layout(self.line_or_trafo_layout, True)
            self.clear_layout(self.new_line_type, True)
            self.clear_layout(self.control_panel_layout, True)
            self.show_spacer()

    def add_line(self, curve):
        self.curves.append(curve)
        self.system.add_line(curve.obj, tuple(curve.coords))

    def add_trafo(self, curve):
        self.curves.append(curve)
        self.system.add_trafo(curve.obj, tuple(curve.coords))

    def add_bus(self):
        """
        Called by: Scene.mouseDoubleClickEvent
        """
        coord = self._curr_element_coord
        curve = self.curve_at(self._curr_element_coord)
        if not isinstance(self.editor.bus_grid[coord], Bus) and not curve:
            bus = self.system.add_bus()
            self.editor.bus_grid[coord] = bus
            self.status_msg.emit_sig("Added bus")
        else:
            self.editor.removeItem(self.editor.drawings[coord])
            self.status_msg.emit_sig("There is an element in this position!")

    def submit_line(self, mode):
        """
        Updates the line parameters based on Y and Z or parameters from LINE_TYPES,
        or converts a trafo into a line and update its parameters following
        Called by: tlSubmitByImpedancePushButton.pressed, tlSubmitByModelPushButton.pressed

        Parameters
        ----------
        mode: either 'parameters' or 'impedance'
        """
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, TransmissionLine):
            # The element already is a line
            line = curve.obj
            if mode == 'parameters':
                param_values = self.find_line_model_from_text()
                # Current selected element is a line
                # Update using properties
                # Z and Y are obtained from the updated properties
                if param_values is not None:
                    ell = float(self.ell_line_edit.text()) * 1e3
                    vbase = float(self.vbase_line_edit.text()) * 1e3
                    self.submit_line_by_model(line, param_values, ell, vbase)
                    self.update_layout()
                    self.status_msg.emit_sig("Updated line with parameters")
                else:
                    self.status_msg.emit_sig("You have to choose a valid model")
            elif mode == 'impedance':
                # Current selected element is a line
                # Update using impedance and admittance
                R = float(self.tl_r_line_edit.text()) / 100
                X = float(self.tl_x_line_edit.text()) / 100
                Y = float(self.tl_b_line_edit.text()) / 100
                Z = R + 1j * X
                Y = 1j * Y
                ell = float(self.ell_line_edit.text()) * 1e3
                vbase = float(self.vbase_line_edit.text()) * 1e3
                self.submit_line_by_impedance(line, Z, Y, ell, vbase)
                self.update_layout()
                self.status_msg.emit_sig("Update line with impedance")
        elif isinstance(curve.obj, Transformer):
            # The element is a trafo and will be converted into a line
            trafo = curve.obj
            self.remove_trafo(curve)
            new_line = TransmissionLine(orig=trafo.orig, dest=trafo.dest)
            if mode == 'parameters':
                param_values = self.find_line_model_from_text()
                if param_values is not None:
                    ell = float(self.ell_line_edit.text()) * 1e3
                    vbase = float(self.vbase_line_edit.text()) * 1e3
                    self.submit_line_by_model(new_line, param_values, ell, vbase)
                    self.status_msg.emit_sig("Trafo -> line, updated with parameters")
                else:
                    self.status_msg.emit_sig("You have to choose a valid model")
            elif mode == 'impedance':
                R = float(self.tl_r_line_edit.text()) / 100
                X = float(self.tl_x_line_edit.text()) / 100
                Y = float(self.tl_b_line_edit.text()) / 100
                Z = R + 1j * X
                Y = 1j * Y
                ell = float(self.ell_line_edit.text()) * 1e3
                vbase = float(self.vbase_line_edit.text()) * 1e3
                self.submit_line_by_impedance(new_line, Z, Y, ell, vbase)
                self.status_msg.emit_sig("Trafo -> line, updated with impedance")
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
            self.update_layout()

    def submit_trafo(self):
        """
        Updates a trafo with the given parameters if the current element is a trafo
        or converts a line into a trafo with the inputted parameters
        Called by: trafoSubmitPushButton.pressed
        """
        curve = self.curve_at(self._curr_element_coord)
        if isinstance(curve.obj, TransmissionLine):
            # Transform line into a trafo
            line = curve.obj
            self.remove_line(curve)
            new_trafo = Transformer(
                orig=line.orig,
                dest=line.dest,
                snom=float(self.snom_trafo_line_edit.text()) * 1e6,
                jx0=float(self.x_zero_seq_trafo_line_edit.text()) / 100,
                jx1=float(self.x_pos_seq_trafo_line_edit.text()) / 100,
                primary=SYMBOL_TO_PY[self.trafo_primary.currentText()],
                secondary=SYMBOL_TO_PY[self.trafo_secondary.currentText()]
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
            self.update_layout()
            self.status_msg.emit_sig("Line -> trafo")
        elif isinstance(curve.obj, Transformer):
            # Update parameters of selected trafo
            trafo = curve.obj
            trafo.snom = float(self.snom_trafo_line_edit.text()) * 1e6
            trafo.jx0 = float(self.x_zero_seq_trafo_line_edit.text()) / 100
            trafo.jx1 = float(self.x_pos_seq_trafo_line_edit.text()) / 100
            trafo.primary = SYMBOL_TO_PY[self.trafo_primary.currentText()]
            trafo.secondary = SYMBOL_TO_PY[self.trafo_secondary.currentText()]
            self.update_layout()
            self.status_msg.emit_sig("Updated trafo parameters")

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
        self.status_msg.emit_sig("Removed trafo")

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
        self.status_msg.emit_sig("Removed line")

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
        Called by: RemoveBus.pressed
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

    def add_gen(self):
        """Adds generation to the bus, make some QLineEdits activated
        Called by: AddGenerationButton.pressed (__init__)
        """
        bus = self.bus_at(self._curr_element_coord)
        self.bus_v_value.setEnabled(True)
        self.xd_line_edit.setEnabled(True)
        if bus.bus_id > 0:
            self.pg_input.setEnabled(True)
        self.gen_ground.setEnabled(True)
        self.add_generation_button.setText('OK')
        self.status_msg.emit_sig("Input generation data...")
        self.add_generation_button.disconnect()
        self.add_generation_button.pressed.connect(self.submit_gen)

    def submit_gen(self):
        """Updates bus parameters with the user input in bus inspector
        Called by: AddedGenerationButton.pressed (add_gen)
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.v = float(self.bus_v_value.text())
            bus.pg = float(self.pg_input.text()) / 100
            bus.gen_ground = self.gen_ground.isChecked()
            if self.xd_line_edit.text() == '\u221E':
                bus.xd = np.inf
            else:
                bus.xd = float(self.xd_line_edit.text()) / 100
            self.bus_v_value.setEnabled(False)
            self.pg_input.setEnabled(False)
            self.xd_line_edit.setEnabled(False)
            self.gen_ground.setEnabled(False)
            self.add_generation_button.disconnect()
            if bus.bus_id > 0:
                self.add_generation_button.setText('-')
                self.add_generation_button.pressed.connect(self.remove_gen)
            else:
                self.add_generation_button.setText('EDIT')
                self.add_generation_button.pressed.connect(self.add_gen)
            self.status_msg.emit_sig("Added generation")

    def remove_gen(self):
        """
        Called by: AddGenerationButton.pressed (submit_gen)
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.v = 1
            bus.pg = 0
            bus.xd = np.inf
            bus.gen_ground = False
            self.bus_menu(bus)
            self.add_generation_button.setText('+')
            self.add_generation_button.disconnect()
            self.add_generation_button.pressed.connect(self.add_gen)
            self.status_msg.emit_sig("Removed generation")

    def add_load(self):
        """
        Called by: AddLoadButton.pressed (__init__)
        """
        self.pl_input.setEnabled(True)
        self.ql_input.setEnabled(True)
        self.load_ground.setEnabled(True)
        self.add_load_button.setText("OK")
        self.status_msg.emit_sig("Input load data...")
        self.add_load_button.disconnect()
        self.add_load_button.pressed.connect(self.submit_load)

    def submit_load(self):
        """
        Called by: AddLoadButton.pressed (add_load)
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.pl = float(self.pl_input.text()) / 100
            bus.ql = float(self.ql_input.text()) / 100
            bus.load_ground = SYMBOL_TO_PY[self.load_ground.currentText()]
            self.pl_input.setEnabled(False)
            self.ql_input.setEnabled(False)
            self.load_ground.setEnabled(False)
            self.add_load_button.setText('-')
            self.add_load_button.disconnect()
            self.add_load_button.pressed.connect(self.remove_load)
            self.status_msg.emit_sig("Added load")

    def remove_load(self):
        """
        Called by: AddLoadButton.pressed (submit_load)
        """
        coord = self._curr_element_coord
        if isinstance(self.editor.bus_grid[coord], Bus):
            bus = self.bus_at(coord)
            bus.pl = 0
            bus.ql = 0
            bus.load_ground = EARTH
            self.bus_menu(bus)
            self.add_load_button.setText('+')
            self.add_load_button.disconnect()
            self.add_load_button.pressed.connect(self.add_load)
            self.status_msg.emit_sig("Removed load")

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
            for curve in self.curves:
                assert curve.obj.orig is not None
                assert curve.obj.dest is not None
                assert curve.obj.dest != curve.obj.orig
        if self.max_niter > 0:
            self.system.update(Nmax=self.max_niter)
        self.update_layout()


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        # Central widget
        self.main_widget = MainWidget()
        self.main_widget.status_msg.signal.connect(self.display_status_msg)
        self.setCentralWidget(self.main_widget)

        self.initUI()

    def initUI(self):
        self.display_status_msg("Ready")
        # Actions
        new_sys = QAction("Start new system", self)
        new_sys.setShortcut("Ctrl+N")
        new_sys.triggered.connect(self.start_new_session)

        save_act = QAction("Save current session", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self.save_session)

        load_act = QAction("Open session", self)
        load_act.setShortcut("Ctrl+O")
        load_act.triggered.connect(self.load_session)

        create_report = QAction("Generate report", self)
        create_report.setShortcut("Ctrl+R")
        create_report.triggered.connect(self.report)

        add_line_act = QAction("Add line type", self)
        add_line_act.setShortcut("Ctrl+L")
        add_line_act.triggered.connect(self.add_line_type)

        edit_line_act = QAction("Edit line type", self)
        edit_line_act.triggered.connect(self.edit_line_type)

        configure_simulation = QAction("Configure simulation", self)
        configure_simulation.setShortcut("Ctrl+X")
        configure_simulation.triggered.connect(self.configure_simulation)

        # Menu bar
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&Session')
        file_menu.addAction(save_act)
        file_menu.addAction(load_act)
        file_menu.addAction(create_report)
        file_menu.addAction(new_sys)

        line_menu = menu_bar.addMenu('&Lines')
        line_menu.addAction(add_line_act)
        line_menu.addAction(edit_line_act)

        settings = menu_bar.addMenu('S&ettings')
        settings.addAction(configure_simulation)

        self.setWindowTitle("Electrical Grid Analysis Tool")
        self.setGeometry(50, 50, 1000, 600)
        self.setMinimumWidth(1000)
        self.show()

    def configure_simulation(self):
        self.main_widget.clear_layout(self.main_widget.bus_layout, True)
        self.main_widget.clear_layout(self.main_widget.line_or_trafo_layout, True)
        self.main_widget.clear_layout(self.main_widget.control_panel_layout, False)
        self.main_widget.update_nmax_slider(self.main_widget.max_niter)
        self.main_widget.update_nmax_label(self.main_widget.max_niter)

    def display_status_msg(self, args):
        self.statusBar().showMessage(args)

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
        self.main_widget.clear_layout(self.main_widget.new_line_type, False)
        self.main_widget.clear_layout(self.main_widget.bus_layout, True)
        self.main_widget.clear_layout(self.main_widget.line_or_trafo_layout, True)
        self.display_status_msg("Adding new line model")

    def edit_line_type(self):
        self.display_status_msg("Editing line types is currently not implemented!")
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
        for bus in self.main_widget.system.buses:
            assert bus in self.main_widget.editor.bus_grid
        for curve in self.main_widget.curves:
            assert curve.obj in self.main_widget.system.lines or\
                   curve.obj in self.main_widget.system.trafos

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
                    point = (square_length / 2 + square_length * j,
                             square_length / 2 + square_length * i)
                    bus = editor.draw_bus(point)
                    editor.drawings[i, j] = bus
        for curve in self.main_widget.curves:
            for pairs in interface_coordpairs(curve.coords, square_length):
                if isinstance(curve.obj, TransmissionLine):
                    dline = editor.draw_line(pairs, color='b')
                else:
                    dline = editor.draw_line(pairs, color='r')
                curve.dlines.append(dline)


def main():
    app = QApplication(sys.argv)
    Window()
    sys.exit(app.exec_())
