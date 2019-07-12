import logging
import os
import shelve
import sys
import traceback

import networkx as nx
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from aspy.core import *
from aspy.methods import update_flow, update_short
from aspy.report import create_report

"""
# ----------------------------------------------------------------------------------------------------
# The global variables are being used to specify the current state of the system    
# ----------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------
# N: graphical grid dimension (N x N - used to initializate the SchemeInputer class)
# ----------------------------------------------------------------------------------------------------
# GRID_BUSES: N X N numpy array that holds core.aspy.Barra elements. It is used 
# to link the SchemeInput graphical interface to the data arrays manipulation
# ----------------------------------------------------------------------------------------------------
# BUSES_PIXMAP: N x N numpy array that holds PyQt5.QtGui.QPixMap items representing
# the buses drawings on SchemeInputer
# ----------------------------------------------------------------------------------------------------
# BUSES: numpy array that holds core.aspy.Barra elements. Each element has the following
# form: [aspy.core.Barra Bus]
# ----------------------------------------------------------------------------------------------------
# LINES: list that holds transmission line elements. Each element has the following form:
# [[aspy.core.LT lines, [PyQt5.QtWidgets.QGraphicsLineItem dlines], [tuple coordinates], bool remove]]
# ----------------------------------------------------------------------------------------------------
# TRANSFORMERS: list that holds transformer elements. Each element has the following form:
# [[aspy.core.Trafo], [PyQt5.QtWidgets.QGraphicsLineItem dlines], [tuple coordinates]]
# ----------------------------------------------------------------------------------------------------
# LINE_TYPES: dictionaries that holds the line parameters to be put into lines
# ----------------------------------------------------------------------------------------------------
"""

MASK = []
N = 20
GRID_BUSES = np.zeros((N, N), object)
BUSES_PIXMAP = np.zeros((N, N), object)
BUSES = []
LINES = []
TRANSFORMERS = []
LINE_TYPES = [['Default', {'r (m)': 2.5e-2, 'd12 (m)': 3.0, 'd23 (m)': 4.5, 'd31 (m)': 7.5, 'd (m)': 0.4,
                           '\u03C1 (\u03A9m)': 1.78e-8, 'm': 2, 'Imax (A)': 1000}]]
LINE_TYPES_HSH = {'r (m)': 'r', '\u03C1 (\u03A9m)': 'rho', 'd12 (m)': 'd12', 'd23 (m)': 'd23', 'd31 (m)': 'd31',
                  'd (m)': 'd', 'm': 'm', 'Imax (A)': 'imax'}
NMAX = 1
OP_MODE = 0


class GenericSignal(QObject):
    signal = pyqtSignal(object)

    def __init__(self):
        super(GenericSignal, self).__init__()

    def emit_sig(self, args):
        self.signal.emit(args)


class SchemeInputer(QGraphicsScene):
    def __init__(self, n=N, length=50, *args, **kwargs):
        super(SchemeInputer, self).__init__(*args, **kwargs)
        self.n = n
        self._oneSquareSideLength = length
        self._moveHistory = np.ones((2, 2)) * -1
        self._selectorHistory = np.array([None, -1, -1])  # 0: old QRect, 1 & 2: coordinates to new QRect
        self._lastRetainer, self._firstRetainer = False, True
        self._pointerSignal = GenericSignal()
        self._methodSignal = GenericSignal()
        self._dataSignal = GenericSignal()
        self.selector_radius = length / 2
        self.setSceneRect(0, 0, self._oneSquareSideLength * self.n,
                          self._oneSquareSideLength * self.n)  # Visible portion of Scene to View
        self.quantizedInterface = self.getQuantizedInterface()
        self.showQuantizedInterface()
        self.setSceneRect(-2 * self._oneSquareSideLength, -2 * self._oneSquareSideLength,
                          self._oneSquareSideLength * (self.n + 4), self._oneSquareSideLength * (self.n + 4))

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

    def Point_pos(self, central_point):
        """
        Parameters
        ----------
        central_point: coordinates of quantized point from interface

        Returns
        -------
        : index codes for point, given its quantized coordinates
        """
        i = int((central_point.y() - self._oneSquareSideLength / 2) / self._oneSquareSideLength)
        j = int((central_point.x() - self._oneSquareSideLength / 2) / self._oneSquareSideLength)
        return i, j

    def mouseReleaseEvent(self, event):
        self._moveHistory[:, :] = -1
        self._lastRetainer = False
        self._firstRetainer = True
        self._methodSignal.emit_sig(3)

    def drawLine(self, coordinates, color='b'):
        """
        Parameters
        ----------
        coordinates: coordinates that guide line drawing

        Returns
        -------
        line: drawn line (PyQt5 object)
        """
        pen = QPen()
        pen.setWidth(2.5)
        if color == 'b':
            pen.setColor(Qt.blue)
        elif color == 'r':
            pen.setColor(Qt.red)
        line = self.addLine(coordinates[0, 0], coordinates[0, 1], coordinates[1, 0], coordinates[1, 1], pen)
        return line

    def drawSquare(self, coordinates):
        """
        Parameters
        ----------
        coordinates: coordinates that guide square drawing

        Returns
        -------
        QRect: drawn square (PyQt5 object)
        """
        pen = QPen()
        pen.setColor(Qt.yellow)
        brush = QBrush()
        brush.setColor(Qt.yellow)
        brush.setStyle(Qt.Dense7Pattern)
        x, y = coordinates
        QRect = self.addRect(x, y, self._oneSquareSideLength, self._oneSquareSideLength, pen, brush)
        return QRect

    def clearSquare(self, oldQRect):
        if oldQRect is not None:
            self.removeItem(oldQRect)

    def drawBus(self, coordinates):
        """
        Parameters
        ----------
        coordinates: coordinates that guide bus drawing

        Returns
        -------
        QRect: drawn bus (PyQt5 object)
        """
        pixmap = QPixmap('./data/icons/DOT.jpg')
        pixmap = pixmap.scaled(self._oneSquareSideLength, self._oneSquareSideLength, Qt.KeepAspectRatio)
        sceneItem = self.addPixmap(pixmap)
        pixmap_coords = coordinates[0] - self._oneSquareSideLength / 2, coordinates[1] - self._oneSquareSideLength / 2
        sceneItem.setPos(pixmap_coords[0], pixmap_coords[1])
        return sceneItem

    def mouseDoubleClickEvent(self, event):
        """This method allows buses additions"""
        global BUSES_PIXMAP
        try:
            double_pressed = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                if self.distance(double_pressed, central_point) <= self.selector_radius:
                    i, j = self.Point_pos(central_point)
                    sceneItem = self.drawBus((central_point.x(), central_point.y()))
                    BUSES_PIXMAP[(i, j)] = sceneItem
                    self._pointerSignal.emit_sig((i, j))
                    self._methodSignal.emit_sig(0)
                    return
        except Exception:
            logging.error(traceback.format_exc())

    def mousePressEvent(self, event):
        """This method allows transmission lines additions"""
        try:
            if event.button() in (1, 2):
                pressed = event.scenePos().x(), event.scenePos().y()
                for central_point in self.quantizedInterface.flatten():
                    if self.distance(pressed, central_point) <= self.selector_radius:
                        i, j = self.Point_pos(central_point)
                        self.clearSquare(self._selectorHistory[0])
                        #  up-right corner is (0, 0)
                        self._selectorHistory[1] = central_point.x() - self._oneSquareSideLength / 2
                        self._selectorHistory[2] = central_point.y() - self._oneSquareSideLength / 2
                        self._selectorHistory[0] = self.drawSquare(self._selectorHistory[1:])
                        self._pointerSignal.emit_sig((i, j))
                        self._methodSignal.emit_sig(4)
                        self._methodSignal.emit_sig(2)
                        return
        except Exception:
            logging.error(traceback.format_exc())

    def mouseMoveEvent(self, event):
        """This method gives behavior to adding lines wire tool"""
        if event.button() == 0:
            clicked = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                i, j = self.Point_pos(central_point)
                try:
                    if self.distance(clicked, central_point) <= self.selector_radius:
                        if np.all(self._moveHistory[0] < 0):  # Set source
                            self._moveHistory[0, 0] = central_point.x()
                            self._moveHistory[0, 1] = central_point.y()
                            if isinstance(GRID_BUSES[i, j], Barra):  # Asserts the start was from a bus
                                self._firstRetainer = False
                        if central_point.x() != self._moveHistory[0, 0] \
                                or central_point.y() != self._moveHistory[0, 1]:  # Set destiny
                            self._moveHistory[1, 0] = central_point.x()
                            self._moveHistory[1, 1] = central_point.y()
                        if (np.all(self._moveHistory > 0)) and \
                                (np.any(self._moveHistory[0, :] != np.any(self._moveHistory[1, :]))):
                            # DRAW LINE #
                            try:
                                if isinstance(GRID_BUSES[i, j], Barra) and not self._firstRetainer:
                                    # when a bus is achieved
                                    line = self.drawLine(self._moveHistory)
                                    self._moveHistory[:, :] = -1
                                    self._lastRetainer = True  # Prevent the user for put line outside last bus
                                    self._pointerSignal.emit_sig((i, j))
                                    self._dataSignal.emit_sig(line)
                                    self._methodSignal.emit_sig(1)
                                elif not isinstance(GRID_BUSES[i, j], Barra) and not (
                                        self._lastRetainer or self._firstRetainer):
                                    # started from a bus
                                    line = self.drawLine(self._moveHistory)
                                    self._moveHistory[:, :] = -1
                                    self._pointerSignal.emit_sig((i, j))
                                    self._dataSignal.emit_sig(line)
                                    self._methodSignal.emit_sig(1)
                            except Exception:
                                logging.error(traceback.format_exc())
                        return
                except Exception:
                    logging.error(traceback.format_exc())

    def getQuantizedInterface(self):
        """
        Returns
        -------
        quantizedInterface: numpy array that holds PyQt QPoint objects with quantized interface coordinates
        """
        quantizedInterface = np.zeros((self.n, self.n), tuple)
        width, height = self.width(), self.height()
        for i in range(self.n):
            for j in range(self.n):
                quantizedInterface[i, j] = \
                    QPoint(width / (2 * self.n) + i * width / self.n, height / (2 * self.n) + j * height / self.n)
        return quantizedInterface

    def showQuantizedInterface(self):
        """Display the quantized interface guidelines"""
        width, height = self.width(), self.height()
        spacing_x, spacing_y = width / self.n, height / self.n
        quantized_x, quantized_y = np.arange(0, width, spacing_x), np.arange(0, height, spacing_y)
        pen = QPen()
        pen.setColor(Qt.lightGray)
        pen.setStyle(Qt.DashDotDotLine)
        for k in range(self.n):
            # Horizontal lines
            self.addLine(0.0, quantized_y[k], width, quantized_y[k], pen)
            # Vertical lines
            self.addLine(quantized_x[k], 0.0, quantized_x[k], height, pen)
        self.addLine(0.0, self.height(), width, self.height(), pen)
        self.addLine(self.width(), 0.0, self.width(), height, pen)


class CircuitInputer(QWidget):
    def __init__(self, parent=None):
        # General initializations
        super(CircuitInputer, self).__init__(parent)
        self.Scene = SchemeInputer()
        self.View = QGraphicsView(self.Scene)
        self.SchemeInputLayout = QHBoxLayout()  # Layout for SchemeInput
        self.SchemeInputLayout.addWidget(self.View)
        self._currElementCoords = None  # Coordinates to current object being manipuled
        self._startNewLT = True
        self._ltorigin = None
        self._temp = None
        self._statusMsg = GenericSignal()
        self.__calls = {0: self.add_bus,
                        1: self.add_line,
                        2: self.LayoutManager,
                        3: self.doAfterMouseRelease,
                        4: self.storeOriginAddLt}
        self.Scene._pointerSignal.signal.connect(lambda args: self.setCurrentObject(args))
        self.Scene._dataSignal.signal.connect(lambda args: self.setTemp(args))
        self.Scene._methodSignal.signal.connect(lambda args: self.methodsTrigger(args))

        # Inspectors
        self.InspectorLayout = QVBoxLayout()

        # Layout for general bar case
        self.BarLayout = QVBoxLayout()

        # Bus title
        self.BarTitle = QLabel('Bar title')
        self.BarTitle.setAlignment(Qt.AlignCenter)
        self.BarTitle.setMinimumWidth(200)

        # Bus voltage
        self.BarV_Value = QLineEdit('0.0')
        self.BarV_Value.setEnabled(False)
        self.BarV_Value.setValidator(QDoubleValidator(0.0, 100.0, 3))

        # Bus angle
        self.BarAngle_Value = QLineEdit('0.0')
        self.BarAngle_Value.setEnabled(False)

        # FormLayout to hold bus data
        self.BarDataFormLayout = QFormLayout()

        # Adding bus voltage and bus angle to bus data FormLayout
        self.BarDataFormLayout.addRow('|V| (pu)', self.BarV_Value)
        self.BarDataFormLayout.addRow('\u03b4 (\u00B0)', self.BarAngle_Value)

        # Label with 'Geração'
        self.AddGenerationLabel = QLabel('Geração')
        self.AddGenerationLabel.setAlignment(Qt.AlignCenter)

        # Button to add generation
        self.AddGenerationButton = QPushButton('+')
        self.AddGenerationButton.pressed.connect(self.add_gen)  # Bind button to make input editable

        # FormLayout to add generation section
        self.AddGenerationFormLayout = QFormLayout()
        self.AddLoadFormLayout = QFormLayout()

        # Line edit to Xd bus
        self.XdLineEdit = QLineEdit('\u221E')
        self.XdLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.XdLineEdit.setEnabled(False)

        # Line edit to input bus Pg
        self.PgInput = QLineEdit('0.0')
        self.PgInput.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.PgInput.setEnabled(False)

        # Line edit to input bus Qg
        self.QgInput = QLineEdit('0.0')
        self.QgInput.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.QgInput.setEnabled(False)

        # Combo box for generation connection
        self.GenConn = QComboBox()
        self.GenConn.addItem('gY')
        self.GenConn.addItem('Y')
        self.GenConn.addItem('\u0394')
        self.GenConn.setDisabled(True)

        # Adding Pg, Qg to add generation FormLayout
        self.AddGenerationFormLayout.addRow('x\'d (pu)', self.XdLineEdit)
        self.AddGenerationFormLayout.addRow('Qg (pu)', self.QgInput)
        self.AddGenerationFormLayout.addRow('Pg (pu)', self.PgInput)
        self.AddGenerationFormLayout.addRow('Con.', self.GenConn)

        # Label with 'Carga'
        self.AddLoadLabel = QLabel('Carga')
        self.AddLoadLabel.setAlignment(Qt.AlignCenter)

        # PushButton that binds to three different methods
        self.AddLoadButton = QPushButton('+')
        self.AddLoadButton.pressed.connect(self.add_load)

        # LineEdit with Ql, Pl
        self.QlInput = QLineEdit('0.0')
        self.QlInput.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.PlInput = QLineEdit('0.0')
        self.PlInput.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.PlInput.setEnabled(False)
        self.QlInput.setEnabled(False)

        # Combo box to load connection
        self.LoadConn = QComboBox()
        self.LoadConn.addItem('gY')
        self.LoadConn.addItem('Y')
        self.LoadConn.addItem('\u0394')
        self.LoadConn.setDisabled(True)

        # Adding Pl and Ql to add load FormLayout
        self.AddLoadFormLayout.addRow('Ql (pu)', self.QlInput)
        self.AddLoadFormLayout.addRow('Pl (pu)', self.PlInput)
        self.AddLoadFormLayout.addRow('Con.', self.LoadConn)

        self.RemoveBus = QPushButton('Remove bus')
        self.RemoveBus.pressed.connect(self.remove_bus)

        self.BarLayout.addWidget(self.BarTitle)
        self.BarLayout.addLayout(self.BarDataFormLayout)
        self.BarLayout.addWidget(self.AddGenerationLabel)
        self.BarLayout.addWidget(self.AddGenerationButton)
        self.BarLayout.addLayout(self.AddGenerationFormLayout)
        self.BarLayout.addWidget(self.AddLoadLabel)
        self.BarLayout.addWidget(self.AddLoadButton)
        self.BarLayout.addLayout(self.AddLoadFormLayout)
        self.BarLayout.addWidget(self.RemoveBus)

        # Layout for input new type of line
        self.InputNewLineType = QVBoxLayout()
        self.InputNewLineTypeFormLayout = QFormLayout()

        self.ModelName = QLineEdit()
        self.ModelName.setValidator(QRegExpValidator(QRegExp("[A-Za-z]*")))
        self.RhoLineEdit = QLineEdit()
        self.RhoLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.rLineEdit = QLineEdit()
        self.rLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.d12LineEdit = QLineEdit()
        self.d12LineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.d23LineEdit = QLineEdit()
        self.d23LineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.d31LineEdit = QLineEdit()
        self.d31LineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.dLineEdit = QLineEdit()
        self.dLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))
        self.mLineEdit = QLineEdit()
        self.mLineEdit.setValidator(QIntValidator(1, 4))
        self.imaxLineEdit = QLineEdit()
        self.imaxLineEdit.setValidator(QIntValidator(1, 1000))

        self.InputNewLineTypeFormLayout.addRow('Nome', self.ModelName)
        self.InputNewLineTypeFormLayout.addRow('\u03C1 (\u03A9m)', self.RhoLineEdit)
        self.InputNewLineTypeFormLayout.addRow('r (m)', self.rLineEdit)
        self.InputNewLineTypeFormLayout.addRow('d12 (m)', self.d12LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d23 (m)', self.d23LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d31 (m)', self.d31LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d (m)', self.dLineEdit)
        self.InputNewLineTypeFormLayout.addRow('m', self.mLineEdit)
        self.InputNewLineTypeFormLayout.addRow('Imax (A)', self.imaxLineEdit)

        self.InputNewLineType.addStretch()
        self.InputNewLineType.addLayout(self.InputNewLineTypeFormLayout)
        self.SubmitNewLineTypePushButton = QPushButton('Submit')
        self.SubmitNewLineTypePushButton.setMinimumWidth(200.0)
        self.SubmitNewLineTypePushButton.pressed.connect(self.addNewLineType)
        self.InputNewLineType.addWidget(self.SubmitNewLineTypePushButton)
        self.InputNewLineType.addStretch()

        # Layout for simulation control panel
        self.ControlPanelLayout = QVBoxLayout()

        self.SimulationControlHbox = QHBoxLayout()
        self.RealTimeRadioButton = QRadioButton()
        self.RealTimeRadioButton.setChecked(True)
        self.RealTimeRadioButton.toggled.connect(lambda: self.setOperationMode(0))
        self.InsertionModeRadioButton = QRadioButton()
        self.InsertionModeRadioButton.toggled.connect(lambda: self.setOperationMode(1))
        self.SimulationControlHbox.addWidget(QLabel('Insertion mode'))
        self.SimulationControlHbox.addWidget(self.InsertionModeRadioButton)
        self.SimulationControlHbox.addWidget(QLabel('Real-time'))
        self.SimulationControlHbox.addWidget(self.RealTimeRadioButton)

        self.NmaxHbox = QHBoxLayout()
        self.NmaxSlider = QSlider()
        self.NmaxSlider.setMinimum(1)
        self.NmaxSlider.setMaximum(20)
        self.NmaxSlider.setOrientation(Qt.Horizontal)
        self.NmaxLabel = QLabel('Nmax: 0{Nmax}'.format(Nmax=NMAX))
        self.NmaxSlider.valueChanged.connect(lambda: self.setNmaxValue(self.NmaxSlider.value()))
        self.NmaxHbox.addWidget(self.NmaxSlider)
        self.NmaxHbox.addWidget(self.NmaxLabel)

        self.ControlPanelLayout.addStretch()
        self.ControlPanelLayout.addLayout(self.SimulationControlHbox)
        self.ControlPanelLayout.addLayout(self.NmaxHbox)
        self.ControlPanelLayout.addStretch()

        # General Layout for LT case
        self.LtOrTrafoLayout = QVBoxLayout()

        self.chooseLt = QRadioButton('LT')
        self.chooseTrafo = QRadioButton('Trafo')
        self.chooseLt.toggled.connect(self.defineLtOrTrafoVisibility)
        self.chooseTrafo.toggled.connect(self.defineLtOrTrafoVisibility)

        self.chooseLtOrTrafo = QHBoxLayout()
        self.chooseLtOrTrafo.addWidget(QLabel('LT/Trafo:'))
        self.chooseLtOrTrafo.addWidget(self.chooseLt)
        self.chooseLtOrTrafo.addWidget(self.chooseTrafo)

        self.choosedLtFormLayout = QFormLayout()

        self.chooseLtModel = QComboBox()
        self.chooseLtModel.addItem('No model')

        self.EllLineEdit = QLineEdit()
        self.EllLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))

        self.VbaseLineEdit = QLineEdit()
        self.VbaseLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 3))

        imp_expr_val = QRegExp("^\d{1,3}\.\d{1,3}[+,-]\d{1,3}\.\d{1,3}\j$")
        self.LtZLineEdit = QLineEdit()
        self.LtZLineEdit.setValidator(QRegExpValidator(imp_expr_val))

        adm_expr_val = QRegExp("^\d{1,1}\.\d{1,3}e[+,-]\d{1,2}j")
        self.LtYLineEdit = QLineEdit()
        self.LtYLineEdit.setValidator(QRegExpValidator(adm_expr_val))

        self.ltSubmitByImpedancePushButton = QPushButton('Submit by impedance')
        self.ltSubmitByImpedancePushButton.setMinimumWidth(200)
        self.ltSubmitByImpedancePushButton.pressed.connect(lambda: self.lineProcessing('impedance'))

        self.ltSubmitByModelPushButton = QPushButton('Submit by model')
        self.ltSubmitByModelPushButton.pressed.connect(lambda: self.lineProcessing('parameters'))
        self.ltSubmitByModelPushButton.setMinimumWidth(200)

        self.choosedLtFormLayout.addRow('Model', self.chooseLtModel)
        self.choosedLtFormLayout.addRow('\u2113 (m)', self.EllLineEdit)
        self.choosedLtFormLayout.addRow('Vbase (V)', self.VbaseLineEdit)
        self.choosedLtFormLayout.addRow('Z (%pu)', self.LtZLineEdit)
        self.choosedLtFormLayout.addRow('Y (%pu)', self.LtYLineEdit)

        self.removeLTPushButton = QPushButton('Remove LT')
        self.removeLTPushButton.setMinimumWidth(200.0)
        self.removeLTPushButton.pressed.connect(self.remove_selected_line)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.removeLTPushButton.pressed.connect(self.LayoutManager)

        self.choosedTrafoFormLayout = QFormLayout()
        self.SNomTrafoLineEdit = QLineEdit()
        self.SNomTrafoLineEdit.setValidator(QDoubleValidator(0, 10.0, 3))
        self.XZeroSeqTrafoLineEdit = QLineEdit()
        self.XZeroSeqTrafoLineEdit.setValidator(QDoubleValidator(0, 10.0, 3))
        self.XPosSeqTrafoLineEdit = QLineEdit()
        self.XPosSeqTrafoLineEdit.setValidator(QDoubleValidator(0, 10.0, 3))

        self.TrafoPrimary = QComboBox()
        self.TrafoPrimary.addItem('Y')
        self.TrafoPrimary.addItem('Yg')
        self.TrafoPrimary.addItem('\u0394')
        self.TrafoSecondary = QComboBox()
        self.TrafoSecondary.addItem('Y')
        self.TrafoSecondary.addItem('Yg')
        self.TrafoSecondary.addItem('\u0394')

        self.trafoSubmitPushButton = QPushButton('Submit trafo')
        self.trafoSubmitPushButton.pressed.connect(self.trafoProcessing)
        self.trafoSubmitPushButton.setMinimumWidth(200)

        self.removeTrafoPushButton = QPushButton('Remove trafo')
        self.removeTrafoPushButton.pressed.connect(self.remove_trafo)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.removeTrafoPushButton.pressed.connect(self.LayoutManager)
        self.removeTrafoPushButton.setMinimumWidth(200)

        self.choosedTrafoFormLayout.addRow('Snom (VA)', self.SNomTrafoLineEdit)
        self.choosedTrafoFormLayout.addRow('x0 (%pu)', self.XZeroSeqTrafoLineEdit)
        self.choosedTrafoFormLayout.addRow('x+ (%pu)', self.XPosSeqTrafoLineEdit)
        self.choosedTrafoFormLayout.addRow('Prim.', self.TrafoPrimary)
        self.choosedTrafoFormLayout.addRow('Sec.', self.TrafoSecondary)

        self.LtOrTrafoLayout.addLayout(self.chooseLtOrTrafo)
        self.LtOrTrafoLayout.addLayout(self.choosedLtFormLayout)
        self.LtOrTrafoLayout.addLayout(self.choosedTrafoFormLayout)

        # Submit and remove buttons for line
        self.LtOrTrafoLayout.addWidget(self.ltSubmitByModelPushButton)
        self.LtOrTrafoLayout.addWidget(self.ltSubmitByImpedancePushButton)
        self.LtOrTrafoLayout.addWidget(self.removeLTPushButton)

        # Buttons submit and remove button for trafo
        self.LtOrTrafoLayout.addWidget(self.trafoSubmitPushButton)
        self.LtOrTrafoLayout.addWidget(self.removeTrafoPushButton)

        # Layout that holds bus inspector and Stretches
        self.InspectorAreaLayout = QVBoxLayout()
        self.InspectorLayout.addStretch()
        self.InspectorLayout.addLayout(self.BarLayout)
        self.InspectorLayout.addLayout(self.LtOrTrafoLayout)
        self.InspectorLayout.addStretch()
        self.InspectorAreaLayout.addLayout(self.InspectorLayout)

        # Toplayout
        self.TopLayout = QHBoxLayout()
        self.Spacer = QSpacerItem(200, 0, 0, 0)
        self.TopLayout.addItem(self.Spacer)
        self.TopLayout.addLayout(self.InspectorAreaLayout)
        self.TopLayout.addLayout(self.SchemeInputLayout)
        self.TopLayout.addLayout(self.InputNewLineType)
        self.TopLayout.addLayout(self.ControlPanelLayout)
        self.setLayout(self.TopLayout)

        # All layouts hidden at first moment
        self.setLayoutHidden(self.BarLayout, True)
        self.setLayoutHidden(self.LtOrTrafoLayout, True)
        self.setLayoutHidden(self.InputNewLineType, True)
        self.setLayoutHidden(self.ControlPanelLayout, True)
        self.showSpacer()


    def updateRealOrInsertionRadio(self, op_mode):
        if not op_mode:
            self.RealTimeRadioButton.setChecked(True)
        else:
            self.InsertionModeRadioButton.setChecked(True)


    def updateNmaxLabel(self, nmax, op_mode):
        if not op_mode:
            if nmax < 10:
                self.NmaxLabel.setText('Nmax: 0{nmax}'.format(nmax=nmax))
            else:
                self.NmaxLabel.setText('Nmax: {nmax}'.format(nmax=nmax))
        else:
            self.NmaxLabel.setText('Nmax: --')


    def updateNmaxSlider(self, nmax, op_mode):
        if not op_mode:
            self.NmaxSlider.setEnabled(True)
            self.NmaxSlider.setValue(nmax)
        else:
            self.NmaxSlider.setDisabled(True)


    def setNmaxValue(self, nmax):
        global NMAX, OP_MODE
        NMAX = nmax
        self.updateNmaxLabel(NMAX, OP_MODE)


    def setOperationMode(self, mode):
        global OP_MODE, NMAX
        OP_MODE = mode
        self.updateNmaxSlider(NMAX, OP_MODE)
        self.updateNmaxLabel(NMAX, OP_MODE)


    def defineLtOrTrafoVisibility(self):
        """Show line or trafo options in adding line/trafo section"""
        if not self.chooseLt.isHidden() and not self.chooseTrafo.isHidden():
            if self.chooseLt.isChecked():
                # Line
                self.setLayoutHidden(self.choosedLtFormLayout, False)
                self.setLayoutHidden(self.choosedTrafoFormLayout, True)
                self.removeLTPushButton.setHidden(False)
                self.ltSubmitByImpedancePushButton.setHidden(False)
                self.ltSubmitByModelPushButton.setHidden(False)
                self.trafoSubmitPushButton.setHidden(True)
                self.removeTrafoPushButton.setHidden(True)
            elif self.chooseTrafo.isChecked():
                # Trafo
                self.setLayoutHidden(self.choosedLtFormLayout, True)
                self.setLayoutHidden(self.choosedTrafoFormLayout, False)
                self.removeLTPushButton.setHidden(True)
                self.ltSubmitByImpedancePushButton.setHidden(True)
                self.ltSubmitByModelPushButton.setHidden(True)
                self.trafoSubmitPushButton.setHidden(False)
                self.removeTrafoPushButton.setHidden(False)

    def updateTrafoInspector(self):
        """Update trafo inspector
        Calls
        -----
        LayoutManager, trafoProcessing
        """
        trafo_code = {0: 'Y', 1: 'Yg', 2: '\u0394'}
        try:
            if self.getTrafoFromGridPos(self._currElementCoords) is not None:
                TRAFO = self.getTrafoFromGridPos(self._currElementCoords)
                trafo = TRAFO[0]
                self.SNomTrafoLineEdit.setText('{:.3g}'.format(trafo.snom))
                self.XZeroSeqTrafoLineEdit.setText('{:.3g}'.format(trafo.jx0 * 100))
                self.XPosSeqTrafoLineEdit.setText('{:.3g}'.format(trafo.jx1 * 100))
                self.TrafoPrimary.setCurrentText(trafo_code[trafo.primary])
                self.TrafoSecondary.setCurrentText(trafo_code[trafo.secondary])
            else:
                self.SNomTrafoLineEdit.setText('1e8')
                self.XZeroSeqTrafoLineEdit.setText('0.0')
                self.XPosSeqTrafoLineEdit.setText('0.0')
                self.TrafoPrimary.setCurrentText(trafo_code[1])
                self.TrafoSecondary.setCurrentText(trafo_code[1])
        except Exception:
            logging.error(traceback.format_exc())

    def updateLtInspector(self):
        """Updates the line inspector
        Calls
        -----
        LayoutManager, lineProcessing
        """
        try:
            LINE = self.getLtFromGridPos(self._currElementCoords)
            line = LINE[0]
            line_model = self.findParametersSetFromLt(line)
            self.EllLineEdit.setText('{:.03g}'.format(line.l))
            self.VbaseLineEdit.setText('{:.03g}'.format(line.vbase))
            self.LtYLineEdit.setText('{number.imag:.03f}j'.format(number=line.Ypu * 100))
            self.LtZLineEdit.setText('{number.real:.03f}{sgn}{number.imag:.03f}j'.format(
                number=line.Zpu * 100, sgn='+' if np.sign(line.Zpu.imag) > 0 else ''))
            self.chooseLtModel.setCurrentText(line_model)
        except Exception:
            logging.error(traceback.format_exc())

    @staticmethod
    def findParametersSetFromLt(LINE):
        """Return the name of parameters set of a existent line or
        return None if the line has been set by impedance and admittance
        """
        global LINE_TYPES
        try:
            line_parameters_name = ['rho', 'r', 'd12', 'd23', 'd31', 'm', 'd']
            line_parameters_val = [LINE.__getattribute__(key) for key in line_parameters_name]
            if line_parameters_val == list(np.ones((7,)) * -1):
                return "No model"
            else:
                for line_type in LINE_TYPES:
                    if all(LINE.__getattribute__(LINE_TYPES_HSH[key]) == line_type[1].get(key) for key in
                        line_type[1].keys()):
                        return line_type[0]
                return "No model"
        except Exception:
            logging.error(traceback.format_exc())

    def findParametersSetFromComboBox(self):
        """Find parameters set based on current selected line or trafo inspector combo box
        If the line was set with impedance/admittance, return 'None'
        """
        set_name = self.chooseLtModel.currentText()
        for line_types in LINE_TYPES:
            if set_name == line_types[0]:
                return line_types[1]
        return None

    def updateLtModelOptions(self):
        """Add the name of a new parameter set to QComboBox choose model,
           if the Combo has not the model yet
        -----------------------------------------------------------------
        """
        for line_type in LINE_TYPES:
            if self.chooseLtModel.isVisible() and self.chooseLtModel.findText(line_type[0]) < 0:
                self.chooseLtModel.addItem(line_type[0])

    def lineProcessing(self, mode):
        """
        Updates the line parameters based on Y and Z or parameters from LINE_TYPES,
        or converts a trafo into a line and update its parameters following
        Calls
        -----
        line and trafo QPushButtons submit by model, submit by parameters
        """
        try:
            if self.getLtFromGridPos(self._currElementCoords) is not None:
                # The element already is a line
                assert (self.getTrafoFromGridPos(self._currElementCoords) is None)
                LINE = self.getLtFromGridPos(self._currElementCoords)
                line = LINE[0]
                if mode == 'parameters':
                    param_values = self.findParametersSetFromComboBox()
                    # Current selected element is a line
                    # Update using properties
                    # Z and Y are obtained from the updated properties
                    if param_values is not None:
                        l = float(self.EllLineEdit.text())
                        vbase = float(self.VbaseLineEdit.text())
                        self.updateLineWithParameters(line, param_values, l, vbase)
                        self.LayoutManager()
                        self._statusMsg.emit_sig('Updated line with parameters')
                    else:
                        self._statusMsg.emit_sig('You have to choose an valid model')
                elif mode == 'impedance':
                    # Current selected element is a line
                    # Update using impedance and admittance
                    Z, Y = complex(self.LtZLineEdit.text()) / 100, complex(self.LtYLineEdit.text()) / 100
                    l = float(self.EllLineEdit.text())
                    vbase = float(self.VbaseLineEdit.text())
                    self.updateLineWithImpedances(line, Z, Y, l, vbase)
                    self.LayoutManager()
                    self._statusMsg.emit_sig('Update line with impedances')
            elif self.getTrafoFromGridPos(self._currElementCoords) is not None:
                # The element is a trafo and will be converted into a line
                assert (self.getLtFromGridPos(self._currElementCoords) is None)
                TRAFO = self.getTrafoFromGridPos(self._currElementCoords)
                self.remove_trafo(TRAFO)
                new_line = LT()
                new_line.origin = TRAFO[0].origin
                new_line.destiny = TRAFO[0].destiny
                if mode == 'parameters':
                    param_values = self.findParametersSetFromComboBox()
                    if param_values is not None:
                        l = float(self.EllLineEdit.text())
                        vbase = float(self.VbaseLineEdit.text())
                        self.updateLineWithParameters(new_line, param_values, l, vbase)
                        self._statusMsg.emit_sig('Trafo -> line, updated with parameters')
                    else:
                        self._statusMsg.emit_sig('You have to choose a valid model')
                elif mode == 'impedance':
                    Z, Y = complex(self.LtZLineEdit.text()) / 100, complex(self.LtYLineEdit.text()) / 100
                    l = float(self.EllLineEdit.text())
                    vbase = float(self.VbaseLineEdit.text())
                    self.updateLineWithImpedances(new_line, Z, Y, l, vbase)
                    self._statusMsg.emit_sig('Trafo -> line, updated with impedances')
                inserting_line = [new_line, TRAFO[1], TRAFO[2], False]
                for line_drawing in inserting_line[1]:
                    blue_pen = QPen()
                    blue_pen.setColor(Qt.blue)
                    blue_pen.setWidth(2.5)
                    line_drawing.setPen(blue_pen)
                    self.Scene.addItem(line_drawing)
                LINES.append(inserting_line)
                self.LayoutManager()
        except Exception:
            logging.error(traceback.format_exc())

    @staticmethod
    def updateLineWithParameters(line, param_values, l, vbase):
        """Update a line with parameters
        Parameters
        ----------
        line: line object to be updated
        param_values: key-value pairs with data do update line
        l: line length in (km)
        vbase: voltage basis to p.u. processes (V)
        """
        line.Z, line.Y = None, None
        line.l = l
        line.vbase = vbase
        line.__dict__.update({LINE_TYPES_HSH[x]: param_values.get(x) for x in param_values})

    @staticmethod
    def updateLineWithImpedances(line, Z, Y, l, vbase):
        """Update a line with impedance/admittance
        Parameters
        ----------
        line: line object to be updated
        Z: impedance (ohm)
        Y: admittance (mho)
        l: line length (km)
        vbase: voltage basis to p.u. processes (V)
        """
        zbase = vbase ** 2 / 1e8
        line.Z, line.Y = Z * zbase, Y / zbase
        line.l = l
        line.vbase = vbase
        line_parameters_name = ['rho', 'r', 'd12', 'd23', 'd31', 'm', 'd']
        updating_line_dict = {key: -1 for key in line_parameters_name}
        line.__dict__.update(updating_line_dict)

    def trafoProcessing(self):
        """
        Updates a trafo with the given parameters if the current element is a trafo
        or converts a line into a trafo with the inputted parameters

        Calls
        -----
        QPushButton Submit trafo
        """
        global TRANSFORMERS
        trafo_code = {'Y': 0, 'Yg': 1, '\u0394': 2}
        try:
            if self.getLtFromGridPos(self._currElementCoords) is not None:
                # Transform line into a trafo
                assert (self.getTrafoFromGridPos(self._currElementCoords) is None)
                line = self.getLtFromGridPos(self._currElementCoords)
                self.remove_selected_line(line)
                new_trafo = Trafo(
                    snom=float(self.SNomTrafoLineEdit.text()),
                    jx0=float(self.XZeroSeqTrafoLineEdit.text()) / 100,
                    jx1=float(self.XPosSeqTrafoLineEdit.text()) / 100,
                    primary=trafo_code[self.TrafoPrimary.currentText()],
                    secondary=trafo_code[self.TrafoSecondary.currentText()],
                    origin=line[0].origin,
                    destiny=line[0].destiny
                )
                inserting_trafo = [new_trafo, line[1], line[2]]
                for line_drawing in inserting_trafo[1]:
                    blue_pen = QPen()
                    blue_pen.setColor(Qt.red)
                    blue_pen.setWidth(2.5)
                    line_drawing.setPen(blue_pen)
                    self.Scene.addItem(line_drawing)
                TRANSFORMERS.append(inserting_trafo)
                self.LayoutManager()
                self._statusMsg.emit_sig('Line -> trafo')
            elif self.getTrafoFromGridPos(self._currElementCoords) is not None:
                # Update parameters of selected trafo
                assert (self.getLtFromGridPos(self._currElementCoords) is None)
                trafo = self.getTrafoFromGridPos(self._currElementCoords)
                trafo[0].snom = float(self.SNomTrafoLineEdit.text())
                trafo[0].jx0 = float(self.XZeroSeqTrafoLineEdit.text()) / 100
                trafo[0].jx1 = float(self.XPosSeqTrafoLineEdit.text()) / 100
                trafo[0].primary = trafo_code[self.TrafoPrimary.currentText()]
                trafo[0].secondary = trafo_code[self.TrafoSecondary.currentText()]
                self.LayoutManager()
                self._statusMsg.emit_sig('Updated trafo parameters')
        except Exception:
            logging.error(traceback.format_exc())

    def addNewLineType(self):
        """Add an new type of line, if given parameters has passed in all the tests"""
        try:
            global LINE_TYPES
            layout = self.InputNewLineTypeFormLayout
            new_values = list(layout.itemAt(i).widget().text() for i in range(layout.count())
                              if not isinstance(layout.itemAt(i), QLayout))
            titles = new_values[:2]
            par_names = new_values[2::2]
            par_values = list(map(lambda x: float(x), new_values[3::2]))
            if any(map(lambda x: x[0] == titles[1], LINE_TYPES)):
                self._statusMsg.emit_sig('Duplicated name. Insert another valid name')
                return
            elif any(map(lambda x: x == '', par_values)):
                self._statusMsg.emit_sig('Undefined parameter. Fill all parameters')
                return
            elif any(map(lambda x: par_values == list(x[1].values()), LINE_TYPES)):
                self._statusMsg.emit_sig('A similar model was identified. The model has not been stored')
                return
            else:
                LINE_TYPES.append([titles[1], {par_names[i]: float(par_values[i]) for i in range(len(par_names))}])
                self._statusMsg.emit_sig('The model has been stored')
        except Exception:
            logging.error(traceback.format_exc())

    def hideSpacer(self):
        self.Spacer.changeSize(0, 0)

    def showSpacer(self):
        self.Spacer.changeSize(200, 0)

    def setLayoutHidden(self, layout, visible):
        """Hide completely any layout containing widgets or/and other layouts"""
        witems = list(layout.itemAt(i).widget() for i in range(layout.count()) \
                      if not isinstance(layout.itemAt(i), QLayout))
        witems = list(filter(lambda x: x is not None, witems))
        for w in witems: w.setHidden(visible)
        litems = list(layout.itemAt(i).layout() for i in range(layout.count()) if isinstance(layout.itemAt(i), QLayout))
        for children_layout in litems: self.setLayoutHidden(children_layout, visible)

    def setTemp(self, args):
        """This method stores the first line in line element drawing during line inputting.
        Its existence is justified by the first square limitation in MouseMoveEvent
        """
        self._temp = args

    def storeOriginAddLt(self):
        if self._startNewLT:
            self._ltorigin = self._currElementCoords

    def add_line(self):
        global LINES
        try:
            if self._startNewLT:
                NEW_LINES = LT(origin=self._ltorigin)
                if not self.checkLineAndTrafoCrossing():
                    LINES.append([NEW_LINES, [], [], False])
                else:
                    LINES.append([NEW_LINES, [], [], True])
                LINES[-1][1].append(self._temp)
                LINES[-1][2].append(self._ltorigin)
                LINES[-1][2].append(self._currElementCoords)
            else:
                if self.checkLineAndTrafoCrossing():
                    LINES[-1][3] = True
                LINES[-1][1].append(self._temp)
                LINES[-1][2].append(self._currElementCoords)
                if isinstance(GRID_BUSES[self._currElementCoords], Barra):
                    if LINES[-1][0].destiny is None:
                        LINES[-1][0].destiny = self._currElementCoords
            self._startNewLT = False
            self._statusMsg.emit_sig('Adding line...')
        except Exception:
            logging.error(traceback.format_exc())

    def checkLineAndTrafoCrossing(self):
        """Searches for crossing between current inputting line/trafo and existent line/trafo"""
        global LINES, TRANSFORMERS
        for tl in LINES:
            if self._currElementCoords in tl[2] and not isinstance(GRID_BUSES[self._currElementCoords], Barra):
                return True
        for trafo in TRANSFORMERS:
            if self._currElementCoords in trafo[2] and not isinstance(GRID_BUSES[self._currElementCoords], Barra):
                return True
        return False

    def remove_trafo(self, trafo=None):
        """Remove an trafo (draw and electrical representation)
        Parameters
        ----------
        trafo: trafo to be removed. If it is None, current selected trafo in interface will be removed
        """
        global TRANSFORMERS
        if not trafo:
            if self.getTrafoFromGridPos(self._currElementCoords) is not None:
                trafo = self.getTrafoFromGridPos(self._currElementCoords)
        for linedrawing in trafo[1]:
            self.Scene.removeItem(linedrawing)
        TRANSFORMERS.remove(trafo)
        if not trafo:
            self._statusMsg.emit_sig('Removed selected trafo')

    def remove_selected_line(self, line=None):
        """Remove an line (draw and electrical representation)

        Parameters
        ----------
        line: line to be removed. If it is None, current selected line in interface will be removed
        """
        global LINES
        if line is None:
            if self.getLtFromGridPos(self._currElementCoords):
                line = self.getLtFromGridPos(self._currElementCoords)
            else:
                pass
        for linedrawing in line[1]:
            self.Scene.removeItem(linedrawing)
        LINES.remove(line)
        self._statusMsg.emit_sig('Removed selected line')

    def remove_pointless_lines(self):
        """
        If line's bool remove is True, the line will be removed.
        The remove may have three causes:
        1. The line crossed with itself or with another line
        2. The line was inputted with only two points
        3. The line has not a destiny bar
        """
        global LINES
        try:
            for line in LINES:
                if line[3]:
                    for linedrawing in line[1]:
                        self.Scene.removeItem(linedrawing)
                    LINES.remove(line)
        except Exception:
            logging.error(traceback.format_exc())

    def doAfterMouseRelease(self):
        global LINES
        self._startNewLT = True
        try:
            if LINES:
                if len(LINES[-1][2]) <= 2:  # If the line has two points only
                    LINES[-1][3] = True  # Remove
                else:  # If the line has more than two points
                    if LINES[-1][0].destiny is None:  # If line has not destiny bus
                        LINES[-1][3] = True  # Remove line
            self.remove_pointless_lines()  # Removes all lines with bool remove = True
            for lt in LINES:
                assert (lt[0].origin is not None)
                assert (lt[0].destiny is not None)
            self.LayoutManager()
            update_mask()
        except Exception:
            logging.error(traceback.format_exc())

    def methodsTrigger(self, args):
        """Trigger methods defined in __calls"""
        self.__calls[args]()

    def setCurrentObject(self, args):
        """Define coordinates pointing to current selected object in interface"""
        self._currElementCoords = args

    def updateBusInspector(self, BUS):
        """Updates the bus inspector with bus data if bus exists or
        show that there's no bus (only after bus exclusion)

        Parameters
        ----------
        BUS: barra object which data will be displayed

        Calls
        -----
        LayoutManager, remove_gen, remove_load
        """
        code = {0: 'gY', 1: 'Y', 2: '\u0394'}
        to_be_desactivated = [self.PgInput,
                              self.PlInput,
                              self.QlInput,
                              self.BarV_Value,
                              self.XdLineEdit,
                              self.LoadConn,
                              self.GenConn]
        for item in to_be_desactivated:
            item.setDisabled(True)
        if BUS:
            print('gen: {0}, load: {1}'.format(code[BUS.gen_conn], code[BUS.load_conn]))
            if BUS.barra_id == 0:
                self.BarTitle.setText('Barra Slack')
            else:
                self.BarTitle.setText('Barra {}'.format(BUS.barra_id))
            if BUS.pl > 0 or BUS.ql > 0:
                self.AddLoadButton.setText('-')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.remove_load)
            else:
                self.AddLoadButton.setText('+')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.add_load)
            if (BUS.pg > 0 or BUS.qg > 0) and BUS.barra_id > 0:
                self.AddGenerationButton.setText('-')
                self.AddGenerationButton.disconnect()
                self.AddGenerationButton.pressed.connect(self.remove_gen)
            else:
                self.AddGenerationButton.setText('+')
                self.AddGenerationButton.disconnect()
                self.AddGenerationButton.pressed.connect(self.add_gen)
            self.BarV_Value.setText('{:.3g}'.format(BUS.v))
            self.BarAngle_Value.setText('{:.3g}'.format(BUS.delta * 180 / np.pi))
            self.QgInput.setText('{:.3g}'.format(BUS.qg))
            self.PgInput.setText('{:.3g}'.format(BUS.pg))
            self.QlInput.setText('{:.3g}'.format(BUS.ql))
            self.PlInput.setText('{:.3g}'.format(BUS.pl))
            self.XdLineEdit.setText('{:.3g}'.format(BUS.xd))
            self.GenConn.setCurrentText(code[BUS.gen_conn])
            self.LoadConn.setCurrentText(code[BUS.load_conn])
        else:
            self.AddLoadButton.setText('+')
            self.AddLoadButton.disconnect()
            self.AddLoadButton.pressed.connect(self.add_load)
        if (BUS.pg > 0 or BUS.qg > 0) and BUS.barra_id > 0:
            self.AddGenerationButton.setText('-')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.remove_gen)
        else:
            self.AddGenerationButton.setText('+')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.add_gen)
        self.BarV_Value.setText('{:.3g}'.format(BUS.v))
        self.BarAngle_Value.setText('{:.3g}'.format(BUS.delta * 180 / np.pi))
        self.QgInput.setText('{:.3g}'.format(BUS.qg))
        self.PgInput.setText('{:.3g}'.format(BUS.pg))
        self.QlInput.setText('{:.3g}'.format(BUS.ql))
        self.PlInput.setText('{:.3g}'.format(BUS.pl))
        if BUS.xd == np.inf:
            self.XdLineEdit.setText('\u221E')
        else:
            self.XdLineEdit.setText('{:.3g}'.format(BUS.xd))

    def LayoutManager(self):
        """Hide or show specific layouts, based on the current element or passed parameters by trigger methods.
        Called two times ever because self.doAfterMouseRelease is triggered whenever the mouse is released
        ------------------------------------------------------------------------------------------------------
        Called by: doAfterMouseRelease
        ------------------------------------------------------------------------------------------------------
        """
        try:
            # Even if there are two elements in a same square, only one will be identified
            # Bus has high priority
            # After, lines and trafo have equal priority
            bus = self.getBusFromGridPos(self._currElementCoords)
            lt = self.getLtFromGridPos(self._currElementCoords)
            trafo = self.getTrafoFromGridPos(self._currElementCoords)
            if bus is not None:
                # Show bus inspect
                self.hideSpacer()
                self.setLayoutHidden(self.InputNewLineType, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, True)
                self.setLayoutHidden(self.ControlPanelLayout, True)
                self.setLayoutHidden(self.BarLayout, False)
                self.updateBusInspector(self.getBusFromGridPos(self._currElementCoords))
            elif lt is not None:
                # Show line inspect
                assert trafo is None
                self.hideSpacer()
                self.setLayoutHidden(self.InputNewLineType, True)
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, False)
                self.chooseLt.setChecked(True)
                self.setLayoutHidden(self.choosedTrafoFormLayout, True)
                self.setLayoutHidden(self.choosedLtFormLayout, False)
                self.trafoSubmitPushButton.setHidden(True)
                self.removeTrafoPushButton.setHidden(True)
                self.setLayoutHidden(self.ControlPanelLayout, True)
                self.removeLTPushButton.setHidden(False)
                self.updateLtModelOptions()
                self.updateLtInspector()
                self.updateTrafoInspector()
            elif trafo is not None:
                # Show trafo inspect
                assert lt is None
                self.setLayoutHidden(self.InputNewLineType, True)
                self.hideSpacer()
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, False)
                self.chooseTrafo.setChecked(True)
                self.setLayoutHidden(self.choosedTrafoFormLayout, False)
                self.setLayoutHidden(self.choosedLtFormLayout, True)
                self.trafoSubmitPushButton.setHidden(False)
                self.removeTrafoPushButton.setHidden(False)
                self.removeLTPushButton.setHidden(True)
                self.ltSubmitByModelPushButton.setHidden(True)
                self.ltSubmitByImpedancePushButton.setHidden(True)
                self.setLayoutHidden(self.ControlPanelLayout, True)
                self.updateTrafoInspector()
            else:
                # No element case
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, True)
                self.setLayoutHidden(self.InputNewLineType, True)
                self.setLayoutHidden(self.ControlPanelLayout, True)
                self.showSpacer()
        except Exception:
            logging.error(traceback.format_exc())

    @staticmethod
    def resequence_buses(buses):
        """Resequence buses id in a array containing barra objects"""
        if 0 in [bus.barra_id for bus in buses]:
            for i in range(len(buses)):
                buses[i].barra_id = i
        else:
            for i in range(1, len(buses) + 1):
                buses[i - 1].barra_id = i

    def add_bus(self):
        try:
            global GRID_BUSES, ID, BUSES, BUSES_PIXMAP
            COORDS = self._currElementCoords
            possible_lt, possible_trafo = self.getLtFromGridPos(COORDS), self.getTrafoFromGridPos(COORDS)
            if not isinstance(GRID_BUSES[COORDS], Barra) and not (possible_lt or possible_trafo):
                if 0 not in [bus.barra_id for bus in BUSES] or np.size(BUSES) == 0:
                    # first add, or add after bus' exclusion
                    SLACK = Barra(barra_id=0, posicao=COORDS)
                    BUSES.insert(0, SLACK)
                    self.resequence_buses(BUSES)
                    GRID_BUSES[COORDS] = SLACK
                elif 0 in [bus.barra_id for bus in BUSES]:
                    # sequenced bus insert
                    BUS = Barra(barra_id=len(BUSES) + 1, posicao=COORDS)
                    GRID_BUSES[COORDS] = BUS
                    BUSES.append(BUS)
                    self.resequence_buses(BUSES)
                self._statusMsg.emit_sig('Added bus')
            else:
                self.Scene.removeItem(BUSES_PIXMAP[COORDS])
                self._statusMsg.emit_sig('There\'s an element in this position!')
        except Exception:
            logging.error(traceback.format_exc())

    def remove_bus(self):
        global ID, BUSES, GRID_BUSES, BUSES_PIXMAP
        try:
            if GRID_BUSES[self._currElementCoords]:
                BUS = self.getBusFromGridPos(self._currElementCoords)
                self.removeElementsLinked2Bus(BUS)
                BUSES.remove(BUS)
                self.resequence_buses(BUSES)
                self.Scene.removeItem(BUSES_PIXMAP[self._currElementCoords])
                BUSES_PIXMAP[self._currElementCoords] = 0
                GRID_BUSES[self._currElementCoords] = 0
                update_mask()
        except Exception:
            logging.error(traceback.format_exc())

    @staticmethod
    def getBusFromGridPos(COORDS):
        """Return a barra object that occupies GRID_BUSES in COORDS position"""
        grid_bus = GRID_BUSES[COORDS]
        if isinstance(grid_bus, Barra):
            for bus in BUSES:
                if bus.posicao == grid_bus.posicao:
                    return bus
        return None

    @staticmethod
    def getLtFromGridPos(COORDS):
        """Return a LT object that have COORDS on its coordinates"""
        for tl in LINES:
            if COORDS in tl[2]:
                return tl
        return None

    @staticmethod
    def getTrafoFromGridPos(COORDS):
        """Return a Trafo object that have COORDS on its coordinates"""
        for trafo in TRANSFORMERS:
            if COORDS in trafo[2]:
                return trafo
        return None

    def removeElementsLinked2Bus(self, BUS):
        global LINES, TRANSFORMERS
        linked_lts, linked_trfs = [], []
        for line in LINES:
            if BUS.posicao in line[2]:
                linked_lts.append(line)
        for removing_lts in linked_lts: self.remove_selected_line(removing_lts)
        for trafo in TRANSFORMERS:
            if BUS.posicao in trafo[2]:
                linked_trfs.append(trafo)
        for removing_trfs in linked_trfs: self.remove_trafo(removing_trfs)

    def add_gen(self):
        """
        Adds generation to the bus, make some QLineEdits activated

        Calls
        -----
        QPushButton Add generation (__init__)
        """
        try:
            global BUSES
            BUS = self.getBusFromGridPos(self._currElementCoords)
            self.BarV_Value.setEnabled(True)
            if BUS.barra_id != 0:
                self.PgInput.setEnabled(True)
                self.XdLineEdit.setEnabled(True)
            self.AddGenerationButton.setText('OK')
            self.GenConn.setEnabled(True)
            self._statusMsg.emit_sig('Input generation data...')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.submit_gen)
        except Exception:
            logging.error(traceback.format_exc())

    def submit_gen(self):
        """Updates bus parameters with the user input in bus inspector

        Calls
        -----
        add_gen (button rebind)
        """
        global GRID_BUSES, BUSES
        if isinstance(GRID_BUSES[self._currElementCoords], Barra):
            gen_code = {'gY': 0, 'Y': 1, '\u0394': 2}
            BUS = self.getBusFromGridPos(self._currElementCoords)
            BUS.v = float(self.BarV_Value.text())
            BUS.pg = float(self.PgInput.text())
            BUS.gen_conn = gen_code[self.GenConn.currentText()]
            if self.XdLineEdit.text() == '\u221E':
                BUS.xd = np.inf
            else:
                BUS.xd = float(self.XdLineEdit.text())
            GRID_BUSES[self._currElementCoords].v = BUS.v
            GRID_BUSES[self._currElementCoords].pg = BUS.pg
            GRID_BUSES[self._currElementCoords].xd = BUS.xd
            GRID_BUSES[self._currElementCoords].gen_conn = BUS.gen_conn
            self.BarV_Value.setEnabled(False)
            self.PgInput.setEnabled(False)
            self.XdLineEdit.setEnabled(False)
            self.GenConn.setDisabled(True)
            self.AddGenerationButton.disconnect()
            if BUS.barra_id:
                self.AddGenerationButton.setText('-')
                self.AddGenerationButton.pressed.connect(self.remove_gen)
            else:
                self.AddGenerationButton.setText('+')
                self.AddGenerationButton.pressed.connect(self.add_gen)
            self._statusMsg.emit_sig('Added generation')

    def remove_gen(self):
        global GRID_BUSES, BUSES
        if isinstance(GRID_BUSES[self._currElementCoords], Barra):
            BUS = self.getBusFromGridPos(self._currElementCoords)
            BUS.v = 1
            BUS.pg = 0
            BUS.xd = np.inf
            BUS.gen_conn = 0
            GRID_BUSES[self._currElementCoords].v = BUS.v
            GRID_BUSES[self._currElementCoords].pg = BUS.pg
            GRID_BUSES[self._currElementCoords].xd = BUS.xd
            GRID_BUSES[self._currElementCoords].gen_conn = 0
            self.updateBusInspector(BUS)
            self.AddGenerationButton.setText('+')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.add_gen)
            self._statusMsg.emit_sig('Removed generation')

    def add_load(self):
        """
        Calls
        -----
        QPushButton Add load (__init__)
        """
        try:
            global BUSES
            self.PlInput.setEnabled(True)
            self.QlInput.setEnabled(True)
            self.AddLoadButton.setText('OK')
            self._statusMsg.emit_sig('Input load data...')
            self.LoadConn.setEnabled(True)
            self.AddLoadButton.disconnect()
            self.AddLoadButton.pressed.connect(self.submit_load)
        except Exception:
            logging.error(traceback.format_exc())

    def submit_load(self):
        """
        Calls
        -----
        add_load (button rebind)
        """
        global GRID_BUSES, BUSES
        try:
            if isinstance(GRID_BUSES[self._currElementCoords], Barra):
                load_code = {'gY': 0, 'Y': 1, '\u0394': 2}
                BUS = self.getBusFromGridPos(self._currElementCoords)
                BUS.pl = float(self.PlInput.text())
                BUS.ql = float(self.QlInput.text())
                BUS.load_conn = load_code[self.LoadConn.currentText()]
                GRID_BUSES[self._currElementCoords].pl = BUS.pl
                GRID_BUSES[self._currElementCoords].ql = BUS.ql
                GRID_BUSES[self._currElementCoords].load_conn = BUS.load_conn
                self.PlInput.setEnabled(False)
                self.QlInput.setEnabled(False)
                self.LoadConn.setEnabled(False)
                self.AddLoadButton.setText('-')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.remove_load)
                self._statusMsg.emit_sig('Added load')
        except Exception:
            logging.error(traceback.format_exc())

    def remove_load(self):
        try:
            global GRID_BUSES, BUSES
            if isinstance(GRID_BUSES[self._currElementCoords], Barra):
                BUS = self.getBusFromGridPos(self._currElementCoords)
                BUS.pl = 0
                BUS.ql = 0
                BUS.load_conn = 0
                GRID_BUSES[self._currElementCoords].pl = 0
                GRID_BUSES[self._currElementCoords].ql = 0
                GRID_BUSES[self._currElementCoords].load_conn = 0
                self.updateBusInspector(BUS)
                self.AddLoadButton.setText('+')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.add_load)
                self._statusMsg.emit_sig('Removed load')
        except Exception:
            logging.error(traceback.format_exc())


class Aspy(QMainWindow):
    def __init__(self):
        super(Aspy, self).__init__()
        self.initUI()

    def initUI(self):
        self.displayStatusMsg('Ready')

        # Actions
        newSys = QAction('Start new system', self)
        newSys.setShortcut('Ctrl+N')
        newSys.triggered.connect(self.startNewSession)

        saveAct = QAction('Save current session', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.saveSession)

        loadAct = QAction('Load current session', self)
        loadAct.setShortcut('Ctrl+O')
        loadAct.triggered.connect(self.loadSession)

        createReport = QAction('Generate report', self)
        createReport.setShortcut('Ctrl+R')
        createReport.triggered.connect(self.report)

        addLineAct = QAction('Add line type', self)
        addLineAct.triggered.connect(self.addLineType)

        editLineAct = QAction('Edit line type', self)
        editLineAct.triggered.connect(self.editLineType)

        configure_simulation = QAction('Configure simulation', self)
        configure_simulation.triggered.connect(self.configureSimulation)

        # Central widget
        self.CircuitInputer = CircuitInputer()
        self.CircuitInputer._statusMsg.signal.connect(lambda args: self.displayStatusMsg(args))
        self.setCentralWidget(self.CircuitInputer)

        # Menu bar
        menubar = self.menuBar()

        filemenu = menubar.addMenu('&Session')
        filemenu.addAction(saveAct)
        filemenu.addAction(loadAct)
        filemenu.addAction(createReport)
        filemenu.addAction(newSys)

        linemenu = menubar.addMenu('&Lines')
        linemenu.addAction(addLineAct)
        linemenu.addAction(editLineAct)

        settings = menubar.addMenu('&Settings')
        settings.addAction(configure_simulation)

        self.setWindowTitle('ASPy')
        self.setGeometry(50, 50, 1000, 600)
        self.setMinimumWidth(1000)
        self.show()

    def configureSimulation(self):
        global NMAX, OP_MODE
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.BarLayout, True)
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.LtOrTrafoLayout, True)
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.ControlPanelLayout, False)
        self.CircuitInputer.updateNmaxSlider(NMAX, OP_MODE)
        self.CircuitInputer.updateNmaxLabel(NMAX, OP_MODE)
        self.CircuitInputer.updateRealOrInsertionRadio(OP_MODE)

    def displayStatusMsg(self, args):
        self.statusBar().showMessage(args, msecs=10000)

    def saveSession(self):
        try:
            sessions_dir = getSessionsDir()
            with shelve.open(os.path.join(sessions_dir, './db')) as db:
                db = storeData(db)
        except Exception:
            logging.error(traceback.format_exc())

    def loadSession(self):
        try:
            sessions_dir = getSessionsDir()
            with shelve.open(os.path.join(sessions_dir, './db')) as db:
                createLocalData(db)
            createSchematic(self.CircuitInputer.Scene)
        except Exception:
            logging.error(traceback.format_exc())

    def report(self):
        global BUSES, LINES, TRANSFORMERS, GRID_BUSES
        create_report(BUSES, LINES, TRANSFORMERS, GRID_BUSES)

    def addLineType(self):
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.InputNewLineType, False)
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.BarLayout, True)
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.LtOrTrafoLayout, True)
        self.displayStatusMsg('Adding new line model')

    def editLineType(self):
        print('edit line type')

    def startNewSession(self):
        global LINES, TRANSFORMERS, BUSES, GRID_BUSES, BUSES_PIXMAP
        self.clear_interface()
        reset_system_state_variables()
        self.CircuitInputer.doAfterMouseRelease()

    def clear_interface(self):
        global BUSES, LINES, TRANSFORMERS, GRID_BUSES, BUSES_PIXMAP
        for line in LINES:
            for graphic in line[1]:
                self.CircuitInputer.Scene.removeItem(graphic)
        for trafo in TRANSFORMERS:
            for graphic in trafo[1]:
                self.CircuitInputer.Scene.removeItem(graphic)
        for bus in BUSES:
            self.CircuitInputer.Scene.removeItem(BUSES_PIXMAP[bus.posicao])

def reset_system_state_variables():
    global BUSES, LINES, TRANSFORMERS, GRID_BUSES, BUSES_PIXMAP
    LINES, BUSES, TRANSFORMERS = [], [], []
    GRID_BUSES = np.zeros((N, N), object)
    BUSES_PIXMAP = np.zeros((N, N), object)

def custom_run(f):
    def wrapper(*args, **kwargs):
        global OP_MODE
        if not OP_MODE:
            f(*args, **kwargs)
    return wrapper

@custom_run
def update_mask():
    global NMAX
    G = nx.Graph()
    for b in BUSES:
        G.add_node(b.barra_id)
    for lt in LINES:
        node1 = GRID_BUSES[lt[0].origin].barra_id
        node2 = GRID_BUSES[lt[0].destiny].barra_id
        G.add_edge(node1, node2)
    for tr in TRANSFORMERS:
        node1 = GRID_BUSES[tr[0].origin].barra_id
        node2 = GRID_BUSES[tr[0].destiny].barra_id
        G.add_edge(node1, node2)
    connected_components = nx.connected_components(G)
    neighbors = []
    for component in connected_components:
        if 0 in component:
            neighbors = component
    MASK = np.zeros(len(BUSES), bool)
    MASK[list(neighbors)] = True
    good_ids = [b.barra_id for b in np.array(BUSES)[MASK]]
    rank = nx.shortest_path_length(G, source=0)
    if len(LINES) > 0:
        mask_linhas = np.ones(len(LINES), bool)
        for i in range(len(LINES)):
            lt = LINES[i][0]
            if GRID_BUSES[lt.origin].barra_id not in good_ids:
                mask_linhas[i] = False
        linhas = np.array(LINES)[mask_linhas][:, 0]
    else:
        linhas = np.array([])
    if len(TRANSFORMERS) > 0:
        mask_trafos = np.ones(len(TRANSFORMERS), bool)
        for i in range(len(TRANSFORMERS)):
            tr = TRANSFORMERS[i][0]
            if GRID_BUSES[tr.origin].barra_id not in good_ids:
                mask_trafos[i] = False
        trafos = np.array(TRANSFORMERS)[mask_trafos][:, 0]
    else:
        trafos = np.array([])
    barras = np.array(BUSES)[MASK]
    hsh = {}
    for j, i in enumerate(good_ids):
        hsh[i] = j
    V, S0 = update_flow(barras, linhas, trafos, GRID_BUSES, NMAX, hsh)
    for b in barras:
        b.v = np.abs(V[hsh[b.barra_id]])
        b.delta = np.angle(V[hsh[b.barra_id]])
        b.pg = np.round(S0[hsh[b.barra_id], 0], 4) + b.pl
        b.qg = np.round(S0[hsh[b.barra_id], 1], 4) + b.ql
        b.rank = rank[b.barra_id]
    for lt in linhas:
        node1 = hsh[GRID_BUSES[lt.origin].barra_id]
        node2 = hsh[GRID_BUSES[lt.destiny].barra_id]
        lt.v1 = V[node1]
        lt.v2 = V[node2]
    for tr in trafos:
        node1 = hsh[GRID_BUSES[tr.origin].barra_id]
        node2 = hsh[GRID_BUSES[tr.destiny].barra_id]
        tr.v1 = V[node1]
        tr.v2 = V[node2]
    If = update_short(barras, linhas, trafos, GRID_BUSES, hsh)
    for b in barras:
        b.iTPG = If[hsh[b.barra_id], 0, 0]
        b.iSLG = If[hsh[b.barra_id], 1, 0]
        b.iDLGb = If[hsh[b.barra_id], 2, 1]
        b.iDLGc = If[hsh[b.barra_id], 2, 2]
        b.iLL = If[hsh[b.barra_id], 3, 1]


def storeData(db):
    global LINES, BUSES, TRANSFORMERS, LINE_TYPES, GRID_BUSES
    filtered_lines = []
    for line in LINES:
        filtered_lines.append([line[0], [], line[2], False])
    db['LINES'] = filtered_lines
    db['BUSES'] = BUSES
    db['GRID_BUSES'] = GRID_BUSES
    filtered_trafos = []
    for trafo in TRANSFORMERS:
        filtered_trafos.append([trafo[0], [], trafo[2], False])  # aspy.core.Trafo/coordinates
    db['TRANSFORMERS'] = filtered_trafos
    db['LINE_TYPES'] = LINE_TYPES
    return db


def createLocalData(db):
    global LINES, BUSES, TRANSFORMERS, LINE_TYPES, GRID_BUSES
    LINE_TYPES = db['LINE_TYPES']
    LINES = db['LINES']
    BUSES = db['BUSES']
    TRANSFORMERS = db['TRANSFORMERS']
    GRID_BUSES = db['GRID_BUSES']
    return LINE_TYPES, LINES, BUSES, TRANSFORMERS, GRID_BUSES


def interface_coordpairs(coords, squarel):
    for k in range(len(coords)-1):
        yield (np.array([[squarel / 2 + squarel * coords[k][1], squarel / 2 + squarel * coords[k][0]],
                         [squarel / 2 + squarel * coords[k + 1][1], squarel / 2 + squarel * coords[k + 1][0]]]))


def createSchematic(scene):
    global LINES, TRANSFORMERS, BUSES
    squarel = scene._oneSquareSideLength
    for bus in BUSES:
        point = squarel / 2 + squarel * bus.posicao[1], squarel / 2 + squarel * bus.posicao[0]
        drawbus = scene.drawBus(point)
        BUSES_PIXMAP[bus.posicao] = drawbus
    for pos, line in enumerate(LINES):
        for pairs in interface_coordpairs(line[2], squarel):
            drawline = scene.drawLine(pairs)
            LINES[pos][1].append(drawline)
    for pos, trafo in enumerate(TRANSFORMERS):
        for pairs in interface_coordpairs(trafo[2], squarel):
            drawline = scene.drawLine(pairs, color='r')
            TRANSFORMERS[pos][1].append(drawline)


def getSessionsDir():
    if sys.platform in ('win32', 'win64'):
        home_dir = os.getenv('userprofile')
        sessions_dir = os.path.join(home_dir, 'Documents\\aspy')
    elif sys.platform == 'linux':
        home_dir = os.getenv('HOME')
        sessions_dir = os.path.join(home_dir, 'aspy')
    else:
        sessions_dir = '.'
    if not os.path.exists(sessions_dir):
        os.mkdir(sessions_dir)
    return sessions_dir


if __name__ == '__main__':
    app = QApplication(sys.argv)
    aspy = Aspy()
    sys.exit(app.exec_())