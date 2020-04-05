import pickle

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .core import *
from .report import create_report
from .utils import *


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


class View(QGraphicsView):
    def __init__(self, QGraphicsScene):
        super(View, self).__init__(QGraphicsScene)
        self.horizontalScrollBar().valueChanged.connect(self.erase)
        self.verticalScrollBar().valueChanged.connect(self.erase)

    def erase(self):
        if self.scene().selectorHistory.dsquare_obj is not None:
            self.scene().removeItem(self.scene().selectorHistory.dsquare_obj)
            self.scene().selectorHistory.dsquare_obj = None


class SchemeInputer(QGraphicsScene):
    def __init__(self, n=20, length=50):
        super(SchemeInputer, self).__init__()
        self.N = n
        self.View = View(self)

        # System state variables
        self.pixmap = np.zeros((self.N, self.N), object)
        self.grid = np.zeros((self.N, self.N), object)
        self.oneSquareSideLength = length
        self.move_history = HistoryData()
        self.block = Block()
        self.selectorHistory = HistoryData()
        self.selectorHistory.__setattr__('dsquare_obj', None)

        self.pointerSignal = GenericSignal()
        self.methodSignal = GenericSignal()
        self.dataSignal = GenericSignal()

        # Visible portion of Scene to View
        self.bump_circle_radius = length / 2
        self.setSceneRect(0,
                          0,
                          self.oneSquareSideLength * self.N,
                          self.oneSquareSideLength * self.N)
        self.quantizedInterface = self.getQuantizedInterface()
        self.showQuantizedInterface()
        self.setSceneRect(self.oneSquareSideLength * -2,
                          self.oneSquareSideLength * -2,
                          self.oneSquareSideLength * (self.N + 4),
                          self.oneSquareSideLength * (self.N + 4))

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
        i = int((central_point.y() - self.oneSquareSideLength / 2) / self.oneSquareSideLength)
        j = int((central_point.x() - self.oneSquareSideLength / 2) / self.oneSquareSideLength)
        return i, j

    def QPoint_from_ij(self, i, j):
        for central_point in self.quantizedInterface.flatten():
            if (i, j) == self.ij_from_QPoint(central_point):
                return central_point

    def drawLine(self, coordinates, color='b'):
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

    def drawSquare(self, coordinates):
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
        rect = self.addRect(x, y, self.oneSquareSideLength, self.oneSquareSideLength, pen, brush)
        return rect

    def drawBus(self, coordinates):
        c = np.array(coordinates) - self.oneSquareSideLength / 4
        pen = QPen(Qt.black)
        brush = QBrush(Qt.SolidPattern)
        ellipse = self.addEllipse(*c, self.oneSquareSideLength / 2, self.oneSquareSideLength / 2, pen, brush)
        return ellipse

    def get_central_point(self, event):
        coordinates = event.scenePos().x(), event.scenePos().y()
        for central_point in self.quantizedInterface.flatten():
            if self.distance(coordinates, central_point) <= self.bump_circle_radius:
                i, j = self.ij_from_QPoint(central_point)
                return central_point, i, j

    def mouseReleaseEvent(self, event):
        self.move_history.reset()
        self.block.start = True
        self.block.end = False
        self.methodSignal.emit_sig(3)

    def mouseDoubleClickEvent(self, event):
        if self.get_central_point(event):
            central_point, i, j = self.get_central_point(event)
            sceneItem = self.drawBus((central_point.x(), central_point.y()))
            self.pixmap[(i, j)] = sceneItem
            self.pointerSignal.emit_sig((i, j))
            self.methodSignal.emit_sig(0)

    def redraw_cursor(self, x, y):
        if self.selectorHistory.dsquare_obj is not None:
            self.removeItem(self.selectorHistory.dsquare_obj)
        self.selectorHistory.set_current(x - self.oneSquareSideLength / 2,
                                         y - self.oneSquareSideLength / 2)
        self.selectorHistory.dsquare_obj = self.drawSquare(self.selectorHistory.current)

    def mousePressEvent(self, event):
        if self.get_central_point(event):
            central_point, i, j = self.get_central_point(event)
            x, y = central_point.x(), central_point.y()
            self.redraw_cursor(x, y)
            self.pointerSignal.emit_sig((i, j))
            self.methodSignal.emit_sig(4)
            self.methodSignal.emit_sig(2)

    @property
    def is_drawing_blocked(self):
        return self.block.start or self.block.end

    def draw_line_suite(self, i, j):
        coordinates = np.atleast_2d(np.array([self.move_history.last, self.move_history.current]))
        line = self.drawLine(coordinates, color='b')
        self.move_history.reset()
        self.pointerSignal.emit_sig((i, j))
        self.dataSignal.emit_sig(line)
        self.methodSignal.emit_sig(1)

    def mouseMoveEvent(self, event):
        if self.get_central_point(event):
            central_point, i, j = self.get_central_point(event)
            if central_point is not None:
                x, y = central_point.x(), central_point.y()
                self.redraw_cursor(x, y)
                if self.move_history.is_empty:
                    self.move_history.set_last(x, y)
                    if isinstance(self.grid[i, j], Bus):
                        self.block.start = False
                if self.move_history.is_last_different_from(x, y):
                    self.move_history.set_current(x, y)
                if self.move_history.allows_drawing and not self.is_drawing_blocked:
                    self.draw_line_suite(i, j)
                    if isinstance(self.grid[i, j], Bus):
                        self.block.end = True

    def getQuantizedInterface(self):
        """
        Returns
        -------
        quantizedInterface: numpy array that holds PyQt QPoint objects with quantized interface coordinates
        """
        quantizedInterface = np.zeros((self.N, self.N), tuple)
        width, height = self.width(), self.height()
        for i in range(self.N):
            for j in range(self.N):
                quantizedInterface[i, j] = QPoint(int(width / (2 * self.N) + i * width / self.N),
                                                  int(height / (2 * self.N) + j * height / self.N))
        return quantizedInterface

    def showQuantizedInterface(self):
        """Display the quantized interface guidelines"""
        width, height = self.width(), self.height()
        spacing_x, spacing_y = width / self.N, height / self.N
        quantized_x, quantized_y = np.arange(0, width, spacing_x), np.arange(0, height, spacing_y)
        pen = QPen()
        pen.setColor(Qt.lightGray)
        pen.setStyle(Qt.DashDotDotLine)
        for k in range(self.N):
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
        self.system = PowerSystem()
        self.line_types = {'Default': TransmissionLine(orig=None, dest=None)}
        self.curves = []
        self.nmax = 20
        self.sidebar_width = 200

        self.Scene = SchemeInputer()

        # self.View = QGraphicsView(self.Scene)
        self.View = self.Scene.View
        self.SchemeInputLayout = QHBoxLayout()  # Layout for SchemeInput
        self.SchemeInputLayout.addWidget(self.View)
        self._currElementCoords = None  # Coordinates to current object being manipuled
        self._startNewTL = True
        self._line_origin = None
        self._temp = None
        self.statusMsg = GenericSignal()
        self.__calls = {0: self.add_bus,
                        1: self.add_segment,
                        2: self.LayoutManager,
                        3: self.doAfterMouseRelease,
                        4: self.storeOriginAddLine}
        self.Scene.pointerSignal.signal.connect(lambda args: self.setCurrentObject(args))
        self.Scene.dataSignal.signal.connect(lambda args: self.setTemp(args))
        self.Scene.methodSignal.signal.connect(lambda args: self.methodsTrigger(args))

        # Inspectors
        self.InspectorLayout = QVBoxLayout()

        # Layout for general bus case
        self.BusLayout = QVBoxLayout()

        # Bus title
        self.BusTitle = QLabel('Bus title')
        self.BusTitle.setAlignment(Qt.AlignCenter)
        self.BusTitle.setMinimumWidth(self.sidebar_width)
        self.BusTitle.setMaximumWidth(self.sidebar_width)

        # Bus voltage
        self.BusV_Value = QLineEdit('0.0')
        self.BusV_Value.setEnabled(False)
        self.BusV_Value.setValidator(QDoubleValidator(bottom=0., top=100.))

        # Bus angle
        self.BusAngle_Value = QLineEdit('0.0')
        self.BusAngle_Value.setEnabled(False)

        # FormLayout to hold bus data
        self.BusDataFormLayout = QFormLayout()

        # Adding bus voltage and bus angle to bus data FormLayout
        self.BusDataFormLayout.addRow('|V| (pu)', self.BusV_Value)
        self.BusDataFormLayout.addRow('\u03b4 (\u00B0)', self.BusAngle_Value)

        # Label with 'Generation'
        self.AddGenerationLabel = QLabel('Generation')
        self.AddGenerationLabel.setAlignment(Qt.AlignCenter)

        # Button to add generation
        self.AddGenerationButton = QPushButton('+')
        self.AddGenerationButton.pressed.connect(self.add_gen)  # Bind button to make input editable

        # FormLayout to add generation section
        self.AddGenerationFormLayout = QFormLayout()
        self.AddLoadFormLayout = QFormLayout()

        # Line edit to Xd bus
        self.XdLineEdit = QLineEdit('\u221E')
        self.XdLineEdit.setValidator(QDoubleValidator())
        self.XdLineEdit.setEnabled(False)

        # Line edit to input bus Pg
        self.PgInput = QLineEdit('0.0')
        self.PgInput.setValidator(QDoubleValidator(bottom=0.))
        self.PgInput.setEnabled(False)

        # Line edit to input bus Qg
        self.QgInput = QLineEdit('0.0')
        self.QgInput.setValidator(QDoubleValidator())
        self.QgInput.setEnabled(False)

        # Check box for generation ground
        self.GenGround = QCheckBox("\u23DA")
        self.GenGround.setEnabled(False)

        # Adding Pg, Qg to add generation FormLayout
        self.AddGenerationFormLayout.addRow('x (%pu)', self.XdLineEdit)
        self.AddGenerationFormLayout.addRow('P<sub>G</sub> (MW)', self.PgInput)
        self.AddGenerationFormLayout.addRow('Q<sub>G</sub> (Mvar)', self.QgInput)
        self.AddGenerationFormLayout.addRow('Y', self.GenGround)

        # Label with 'Load'
        self.AddLoadLabel = QLabel('Load')
        self.AddLoadLabel.setAlignment(Qt.AlignCenter)

        # PushButton that binds to three different methods
        self.AddLoadButton = QPushButton('+')
        self.AddLoadButton.pressed.connect(self.add_load)

        # LineEdit with Ql, Pl
        self.QlInput = QLineEdit('0.0')
        self.QlInput.setValidator(QDoubleValidator())
        self.PlInput = QLineEdit('0.0')
        self.PlInput.setValidator(QDoubleValidator())
        self.PlInput.setEnabled(False)
        self.QlInput.setEnabled(False)

        # Check box to load ground
        # self.LoadGround = QCheckBox("\u23DA")
        self.LoadGround = QComboBox()
        self.LoadGround.addItem("Y")
        self.LoadGround.addItem("Y\u23DA")
        self.LoadGround.addItem("\u0394")
        self.LoadGround.setEnabled(False)

        # Adding Pl and Ql to add load FormLayout
        self.AddLoadFormLayout.addRow('P<sub>L</sub> (MW)', self.PlInput)
        self.AddLoadFormLayout.addRow('Q<sub>L</sub> (Mvar)', self.QlInput)
        self.AddLoadFormLayout.addRow('Y', self.LoadGround)

        self.RemoveBus = QPushButton('Remove bus')
        self.RemoveBus.pressed.connect(self.remove_bus)

        self.BusLayout.addWidget(self.BusTitle)
        self.BusLayout.addLayout(self.BusDataFormLayout)
        self.BusLayout.addWidget(self.AddGenerationLabel)
        self.BusLayout.addWidget(self.AddGenerationButton)
        self.BusLayout.addLayout(self.AddGenerationFormLayout)
        self.BusLayout.addWidget(self.AddLoadLabel)
        self.BusLayout.addWidget(self.AddLoadButton)
        self.BusLayout.addLayout(self.AddLoadFormLayout)
        self.BusLayout.addWidget(self.RemoveBus)

        # Layout for input new type of line
        self.InputNewLineType = QVBoxLayout()
        self.InputNewLineTypeFormLayout = QFormLayout()

        self.ModelName = QLineEdit()
        self.ModelName.setValidator(QRegExpValidator(QRegExp("[A-Za-z]*")))
        self.RhoLineEdit = QLineEdit()
        self.RhoLineEdit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.rLineEdit = QLineEdit()
        self.rLineEdit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d12LineEdit = QLineEdit()
        self.d12LineEdit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d23LineEdit = QLineEdit()
        self.d23LineEdit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.d31LineEdit = QLineEdit()
        self.d31LineEdit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.dLineEdit = QLineEdit()
        self.dLineEdit.setValidator(QDoubleValidator(bottom=0., top=100.))
        self.mLineEdit = QLineEdit()
        self.mLineEdit.setValidator(QIntValidator(bottom=1, top=4))
        self.imaxLineEdit = QLineEdit()
        self.imaxLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.InputNewLineTypeFormLayout.addRow('Name', self.ModelName)
        self.InputNewLineTypeFormLayout.addRow('\u03C1 (n\u03A9m)', self.RhoLineEdit)
        self.InputNewLineTypeFormLayout.addRow('r (mm)', self.rLineEdit)
        self.InputNewLineTypeFormLayout.addRow('d12 (m)', self.d12LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d23 (m)', self.d23LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d31 (m)', self.d31LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d (m)', self.dLineEdit)
        self.InputNewLineTypeFormLayout.addRow('m', self.mLineEdit)
        self.InputNewLineTypeFormLayout.addRow('Imax (A)', self.imaxLineEdit)

        self.InputNewLineType.addStretch()
        self.InputNewLineType.addLayout(self.InputNewLineTypeFormLayout)
        self.SubmitNewLineTypePushButton = QPushButton('Submit')
        self.SubmitNewLineTypePushButton.setMinimumWidth(self.sidebar_width)
        self.SubmitNewLineTypePushButton.setMaximumWidth(self.sidebar_width)
        self.SubmitNewLineTypePushButton.pressed.connect(self.addNewLineType)
        self.InputNewLineType.addWidget(self.SubmitNewLineTypePushButton)
        self.InputNewLineType.addStretch()

        # Layout for simulation control panel
        self.ControlPanelLayout = QVBoxLayout()

        self.NmaxHbox = QHBoxLayout()
        self.NmaxSlider = QSlider()
        self.NmaxSlider.setMinimum(0)
        self.NmaxSlider.setMaximum(50)
        self.NmaxSlider.setOrientation(Qt.Vertical)
        self.NmaxLabel = QLabel('Nmax: {:02d}'.format(self.nmax))
        self.NmaxSlider.valueChanged.connect(lambda: self.setNmaxValue(self.NmaxSlider.value()))
        self.NmaxHbox.addWidget(self.NmaxLabel)
        self.NmaxHbox.addWidget(self.NmaxSlider)

        self.ControlPanelLayout.addStretch()
        self.ControlPanelLayout.addLayout(self.NmaxHbox)
        self.ControlPanelLayout.addStretch()

        # General Layout for TL case
        self.LineOrTrafoLayout = QVBoxLayout()

        self.chooseLine = QRadioButton('TL')
        self.chooseTrafo = QRadioButton('TRAFO')
        self.chooseLine.toggled.connect(self.defineLineOrTrafoVisibility)
        self.chooseTrafo.toggled.connect(self.defineLineOrTrafoVisibility)

        self.chooseLineOrTrafo = QHBoxLayout()
        self.chooseLineOrTrafo.addWidget(QLabel('TL/TRAFO:'))
        self.chooseLineOrTrafo.addWidget(self.chooseLine)
        self.chooseLineOrTrafo.addWidget(self.chooseTrafo)

        self.chosenLineFormLayout = QFormLayout()

        self.chooseLineModel = QComboBox()
        self.chooseLineModel.addItem('No model')

        self.EllLineEdit = QLineEdit()
        self.EllLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.VbaseLineEdit = QLineEdit()
        self.VbaseLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.TlRLineEdit = QLineEdit()
        self.TlRLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.TlXLineEdit = QLineEdit()
        self.TlXLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.TlYLineEdit = QLineEdit()
        self.TlYLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.tlSubmitByImpedancePushButton = QPushButton('Submit by impedance')
        self.tlSubmitByImpedancePushButton.setMinimumWidth(self.sidebar_width)
        self.tlSubmitByImpedancePushButton.setMaximumWidth(self.sidebar_width)
        self.tlSubmitByImpedancePushButton.pressed.connect(lambda: self.lineProcessing('impedance'))

        self.tlSubmitByModelPushButton = QPushButton('Submit by model')
        self.tlSubmitByModelPushButton.pressed.connect(lambda: self.lineProcessing('parameters'))
        self.tlSubmitByModelPushButton.setMinimumWidth(self.sidebar_width)
        self.tlSubmitByModelPushButton.setMaximumWidth(self.sidebar_width)

        self.chosenLineFormLayout.addRow('Model', self.chooseLineModel)
        self.chosenLineFormLayout.addRow('\u2113 (km)', self.EllLineEdit)
        self.chosenLineFormLayout.addRow('Vbase (kV)', self.VbaseLineEdit)
        self.chosenLineFormLayout.addRow('R (%pu)', self.TlRLineEdit)
        self.chosenLineFormLayout.addRow('X<sub>L</sub> (%pu)', self.TlXLineEdit)
        self.chosenLineFormLayout.addRow('B<sub>C</sub> (%pu)', self.TlYLineEdit)

        self.removeTLPushButton = QPushButton('Remove TL')
        self.removeTLPushButton.setMinimumWidth(self.sidebar_width)
        self.removeTLPushButton.setMaximumWidth(self.sidebar_width)
        self.removeTLPushButton.pressed.connect(self.remove_line)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.removeTLPushButton.pressed.connect(self.LayoutManager)

        self.chosenTrafoFormLayout = QFormLayout()
        self.SNomTrafoLineEdit = QLineEdit()
        self.SNomTrafoLineEdit.setValidator(QDoubleValidator(bottom=0.))
        self.XZeroSeqTrafoLineEdit = QLineEdit()
        self.XZeroSeqTrafoLineEdit.setValidator(QDoubleValidator(bottom=0.))
        self.XPosSeqTrafoLineEdit = QLineEdit()
        self.XPosSeqTrafoLineEdit.setValidator(QDoubleValidator(bottom=0.))

        self.TrafoPrimary = QComboBox()
        self.TrafoPrimary.addItem('Y')
        self.TrafoPrimary.addItem('Y\u23DA')
        self.TrafoPrimary.addItem('\u0394')
        self.TrafoSecondary = QComboBox()
        self.TrafoSecondary.addItem('Y')
        self.TrafoSecondary.addItem('Y\u23DA')
        self.TrafoSecondary.addItem('\u0394')

        self.trafoSubmitPushButton = QPushButton('Submit trafo')
        self.trafoSubmitPushButton.pressed.connect(self.trafoProcessing)
        self.trafoSubmitPushButton.setMinimumWidth(self.sidebar_width)
        self.trafoSubmitPushButton.setMaximumWidth(self.sidebar_width)

        self.removeTrafoPushButton = QPushButton('Remove trafo')
        self.removeTrafoPushButton.pressed.connect(self.remove_trafo)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.removeTrafoPushButton.pressed.connect(self.LayoutManager)
        self.removeTrafoPushButton.setMinimumWidth(self.sidebar_width)
        self.removeTrafoPushButton.setMaximumWidth(self.sidebar_width)

        self.chosenTrafoFormLayout.addRow('Snom (MVA)', self.SNomTrafoLineEdit)
        self.chosenTrafoFormLayout.addRow('x+ (%pu)', self.XPosSeqTrafoLineEdit)
        self.chosenTrafoFormLayout.addRow('x0 (%pu)', self.XZeroSeqTrafoLineEdit)
        self.chosenTrafoFormLayout.addRow('Prim.', self.TrafoPrimary)
        self.chosenTrafoFormLayout.addRow('Sec.', self.TrafoSecondary)

        self.LineOrTrafoLayout.addLayout(self.chooseLineOrTrafo)
        self.LineOrTrafoLayout.addLayout(self.chosenLineFormLayout)
        self.LineOrTrafoLayout.addLayout(self.chosenTrafoFormLayout)

        # Submit and remove buttons for line
        self.LineOrTrafoLayout.addWidget(self.tlSubmitByModelPushButton)
        self.LineOrTrafoLayout.addWidget(self.tlSubmitByImpedancePushButton)
        self.LineOrTrafoLayout.addWidget(self.removeTLPushButton)

        # Buttons submit and remove button for trafo
        self.LineOrTrafoLayout.addWidget(self.trafoSubmitPushButton)
        self.LineOrTrafoLayout.addWidget(self.removeTrafoPushButton)

        # Layout that holds bus inspector and Stretches
        self.InspectorAreaLayout = QVBoxLayout()
        self.InspectorLayout.addStretch()
        self.InspectorLayout.addLayout(self.BusLayout)
        self.InspectorLayout.addLayout(self.LineOrTrafoLayout)
        self.InspectorLayout.addStretch()
        self.InspectorAreaLayout.addLayout(self.InspectorLayout)

        # Toplayout
        self.TopLayout = QHBoxLayout()
        self.Spacer = QSpacerItem(self.sidebar_width, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.TopLayout.addItem(self.Spacer)
        self.TopLayout.addLayout(self.InspectorAreaLayout)
        self.TopLayout.addLayout(self.SchemeInputLayout)
        self.TopLayout.addLayout(self.InputNewLineType)
        self.TopLayout.addLayout(self.ControlPanelLayout)
        self.setLayout(self.TopLayout)

        # All layouts hidden at first moment
        self.setLayoutHidden(self.BusLayout, True)
        self.setLayoutHidden(self.LineOrTrafoLayout, True)
        self.setLayoutHidden(self.InputNewLineType, True)
        self.setLayoutHidden(self.ControlPanelLayout, True)
        self.showSpacer()

    def methodsTrigger(self, args):
        """Trigger methods defined in __calls"""
        self.__calls[args]()

    def setCurrentObject(self, args):
        """Define coordinates pointing to current selected object in interface"""
        self._currElementCoords = args

    def hideSpacer(self):
        self.Spacer.changeSize(0, 0)

    def showSpacer(self):
        self.Spacer.changeSize(self.sidebar_width, 0)

    def setTemp(self, args):
        """This method stores the first line in line element drawing during line inputting.
        Its existence is justified by the first square limitation in MouseMoveEvent
        """
        self._temp = args

    def storeOriginAddLine(self):
        if self._startNewTL:
            self._line_origin = self._currElementCoords

    def setLayoutHidden(self, layout, visible):
        """Hide completely any layout containing widgets or/and other layouts"""
        witems = list(layout.itemAt(i).widget() for i in range(layout.count())
                      if not isinstance(layout.itemAt(i), QLayout))
        witems = list(filter(lambda x: x is not None, witems))
        for w in witems:
            w.setHidden(visible)
        litems = list(layout.itemAt(i).layout() for i in range(layout.count()) if isinstance(layout.itemAt(i), QLayout))
        for children_layout in litems:
            self.setLayoutHidden(children_layout, visible)

    def updateNmaxLabel(self, nmax):
        self.NmaxLabel.setText('Nmax: {}'.format(nmax).zfill(2))

    def updateNmaxSlider(self, nmax):
        self.NmaxSlider.setEnabled(True)
        self.NmaxSlider.setValue(nmax)

    def setNmaxValue(self, nmax):
        self.nmax = nmax
        self.updateNmaxLabel(self.nmax)

    def getBusFromGridPos(self, coords):
        """Returns a Bus object that occupies grid in `coords` position"""
        grid_bus = self.Scene.grid[coords]
        if isinstance(grid_bus, Bus):
            return grid_bus
        return None

    def getCurveFromGridPos(self, coords):
        """Returns a LineSegment object that has `coords` in its coordinates"""
        for curve in self.curves:
            if coords in curve.coords:
                return curve
        return None

    def checkLineAndTrafoCrossing(self):
        """Searches for crossing between current inputting line/trafo and existent line/trafo"""
        for curve in self.curves:
            if self._currElementCoords in curve.coords and not isinstance(self.Scene.grid[self._currElementCoords],
                                                                          Bus):
                return True
        return False

    def add_segment(self):
        if self._startNewTL:
            bus_orig = self.Scene.grid[self._line_origin]
            new_line = TransmissionLine(orig=bus_orig, dest=None)
            new_curve = LineSegment(obj=new_line,
                                    coords=[self._line_origin, self._currElementCoords],
                                    dlines=[self._temp])
            if self.checkLineAndTrafoCrossing():
                new_curve.remove = True
            self.curves.append(new_curve)
        else:
            curr_curve = self.curves[-1]
            if self.checkLineAndTrafoCrossing():
                curr_curve.remove = True
            curr_curve.dlines.append(self._temp)
            curr_curve.coords.append(self._currElementCoords)
            if isinstance(self.Scene.grid[self._currElementCoords], Bus):
                if curr_curve.obj.dest is None:
                    bus_dest = self.Scene.grid[self._currElementCoords]
                    curr_curve.obj.dest = bus_dest
        self._startNewTL = False
        self.statusMsg.emit_sig('Adding line...')

    def findParametersSetFromLt(self, line):
        """Return the name of parameters set of a existent line or
        return None if the line has been set by impedance and admittance
        """
        for line_name, line_model in self.line_types.items():
            if line_model.param == line.param:
                return line_name
        return "No model"

    def findParametersSetFromComboBox(self):
        """Find parameters set based on current selected line or trafo inspector combo box
        If the line was set with impedance/admittance, return 'None'
        """
        set_name = self.chooseLineModel.currentText()
        for line_name, line_model in self.line_types.items():
            if set_name == line_name:
                return line_model
        return None

    def addNewLineType(self):
        """Add a new type of line, if given parameters has passed in all the tests
        Called by: SubmitNewLineTypePushButton.pressed"""
        name = self.ModelName.text()
        float_or_nan = lambda s: np.nan if s == '' else float(s)
        new_param = dict(
            r=float_or_nan(self.rLineEdit.text()) / 1e3,
            d12=float_or_nan(self.d12LineEdit.text()),
            d23=float_or_nan(self.d23LineEdit.text()),
            d31=float_or_nan(self.d31LineEdit.text()),
            d=float_or_nan(self.dLineEdit.text()),
            rho=float_or_nan(self.RhoLineEdit.text()) / 1e9,
            m=float_or_nan(self.mLineEdit.text()),
            imax=float_or_nan(self.imaxLineEdit.text())
        )
        line = TransmissionLine(orig=None, dest=None)
        line.__dict__.update(new_param)
        if name in self.line_types.keys():
            self.statusMsg.emit_sig('Duplicated name. Insert another valid name')
            return
        if any(np.isnan(list(new_param.values()))):
            self.statusMsg.emit_sig('Undefined parameter. Fill all parameters')
            return
        if any(map(lambda x: line.param == x.param, self.line_types.values())):
            self.statusMsg.emit_sig('A similar model was identified. The model has not been stored')
            return
        self.line_types[name] = line
        self.statusMsg.emit_sig('The model has been stored')

    @staticmethod
    def updateLineWithParameters(line, param_values, ell, vbase):
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
    def updateLineWithImpedances(line, Z, Y, ell, vbase):
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

    def updateLineModelOptions(self):
        """Add the name of a new parameter set to QComboBox choose model,
           if the Combo has not the model yet
        -----------------------------------------------------------------
        """
        for line_name in self.line_types.keys():
            if self.chooseLineModel.isVisible() and self.chooseLineModel.findText(line_name) < 0:
                self.chooseLineModel.addItem(line_name)

    def defineLineOrTrafoVisibility(self):
        """Show line or trafo options in adding line/trafo section"""
        if not self.chooseLine.isHidden() and not self.chooseTrafo.isHidden():
            if self.chooseLine.isChecked():
                # Line
                self.setLayoutHidden(self.chosenLineFormLayout, False)
                self.setLayoutHidden(self.chosenTrafoFormLayout, True)
                self.removeTLPushButton.setHidden(False)
                self.tlSubmitByImpedancePushButton.setHidden(False)
                self.tlSubmitByModelPushButton.setHidden(False)
                self.trafoSubmitPushButton.setHidden(True)
                self.removeTrafoPushButton.setHidden(True)
            elif self.chooseTrafo.isChecked():
                # Trafo
                self.setLayoutHidden(self.chosenLineFormLayout, True)
                self.setLayoutHidden(self.chosenTrafoFormLayout, False)
                self.removeTLPushButton.setHidden(True)
                self.tlSubmitByImpedancePushButton.setHidden(True)
                self.tlSubmitByModelPushButton.setHidden(True)
                self.trafoSubmitPushButton.setHidden(False)
                self.removeTrafoPushButton.setHidden(False)

    def updateTrafoInspector(self):
        """Update trafo inspector
        Calls
        -----
        LayoutManager, trafoProcessing
        """
        curve = self.getCurveFromGridPos(self._currElementCoords)
        if curve is not None:
            trafo = curve.obj
            self.SNomTrafoLineEdit.setText('{:.3g}'.format(trafo.snom / 1e6))
            self.XZeroSeqTrafoLineEdit.setText('{:.3g}'.format(trafo.jx0 * 100))
            self.XPosSeqTrafoLineEdit.setText('{:.3g}'.format(trafo.jx1 * 100))
            self.TrafoPrimary.setCurrentText(PY_TO_SYMBOL[trafo.primary])
            self.TrafoSecondary.setCurrentText(PY_TO_SYMBOL[trafo.secondary])
        else:
            self.SNomTrafoLineEdit.setText('100')
            self.XZeroSeqTrafoLineEdit.setText('0.0')
            self.XPosSeqTrafoLineEdit.setText('0.0')
            self.TrafoPrimary.setCurrentText(PY_TO_SYMBOL[1])
            self.TrafoSecondary.setCurrentText(PY_TO_SYMBOL[1])

    def updateLineInspector(self):
        """Updates the line inspector
        Calls
        -----
        LayoutManager, lineProcessing
        """
        curve = self.getCurveFromGridPos(self._currElementCoords)
        line = curve.obj
        line_model = self.findParametersSetFromLt(line)
        self.EllLineEdit.setText('{:.03g}'.format(line.ell / 1e3))
        self.VbaseLineEdit.setText('{:.03g}'.format(line.vbase / 1e3))
        self.TlRLineEdit.setText('{number.real:.04f}'.format(number=line.Zpu * 100))
        self.TlXLineEdit.setText('{number.imag:.04f}'.format(number=line.Zpu * 100))
        self.TlYLineEdit.setText('{number.imag:.04f}'.format(number=line.Ypu * 100))
        self.chooseLineModel.setCurrentText(line_model)

    def updateBusInspector(self, bus):
        """Updates the bus inspector with bus data if bus exists or
        shows that there's no bus (only after bus exclusion)
        Called by: LayoutManager, remove_gen, remove_load

        Parameters
        ----------
        bus: Bus object whose data will be displayed
        """
        to_be_disabled = [self.PgInput,
                          self.PlInput,
                          self.QlInput,
                          self.BusV_Value,
                          self.XdLineEdit,
                          self.LoadGround,
                          self.GenGround]
        for item in to_be_disabled:
            item.setDisabled(True)
        if bus:
            if bus.bus_id == 0:
                self.BusTitle.setText('Slack')
            else:
                self.BusTitle.setText('Bus {}'.format(bus.bus_id))
            if bus.pl > 0 or bus.ql > 0:
                self.AddLoadButton.setText('-')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.remove_load)
                self.LoadGround.setCurrentText(PY_TO_SYMBOL[bus.load_ground])
            else:
                self.AddLoadButton.setText('+')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.add_load)
                self.LoadGround.setCurrentText(PY_TO_SYMBOL[EARTH])
            if (bus.pg > 0 or bus.qg > 0) and bus.bus_id > 0:
                self.AddGenerationButton.setText('-')
                self.AddGenerationButton.disconnect()
                self.AddGenerationButton.pressed.connect(self.remove_gen)
            elif bus.bus_id == 0:
                self.AddGenerationButton.setText('EDIT')
                self.AddGenerationButton.disconnect()
                self.AddGenerationButton.pressed.connect(self.add_gen)
            else:
                self.AddGenerationButton.setText('+')
                self.AddGenerationButton.disconnect()
                self.AddGenerationButton.pressed.connect(self.add_gen)
            self.BusV_Value.setText('{:.3g}'.format(bus.v))
            self.BusAngle_Value.setText('{:.3g}'.format(bus.delta * 180 / np.pi))
            self.QgInput.setText('{:.4g}'.format(bus.qg * 100))
            self.PgInput.setText('{:.4g}'.format(bus.pg * 100))
            self.QlInput.setText('{:.4g}'.format(bus.ql * 100))
            self.PlInput.setText('{:.4g}'.format(bus.pl * 100))
            self.XdLineEdit.setText('{:.3g}'.format(bus.xd))
            self.GenGround.setChecked(bus.gen_ground)

        if bus.xd == np.inf:
            self.XdLineEdit.setText('\u221E')
        else:
            self.XdLineEdit.setText('{:.3g}'.format(bus.xd * 100))

    def LayoutManager(self):
        """Hide or show specific layouts, based on the current element or passed parameters by trigger methods.
        Called two times ever because self.doAfterMouseRelease is triggered whenever the mouse is released
        ------------------------------------------------------------------------------------------------------
        Called by: doAfterMouseRelease
        ------------------------------------------------------------------------------------------------------
        """

        # Even if there are two elements in a same square, only one will be identified
        # Bus has high priority
        # After, lines and trafo have equal priority
        bus = self.getBusFromGridPos(self._currElementCoords)
        curve = self.getCurveFromGridPos(self._currElementCoords)
        if bus is not None:
            # Show bus inspect
            self.hideSpacer()
            self.setLayoutHidden(self.InputNewLineType, True)
            self.setLayoutHidden(self.LineOrTrafoLayout, True)
            self.setLayoutHidden(self.ControlPanelLayout, True)
            self.setLayoutHidden(self.BusLayout, False)
            self.updateBusInspector(bus)
        elif curve is not None:
            if isinstance(curve.obj, TransmissionLine):
                # Show line inspect
                self.hideSpacer()
                self.setLayoutHidden(self.InputNewLineType, True)
                self.setLayoutHidden(self.BusLayout, True)
                self.setLayoutHidden(self.LineOrTrafoLayout, False)
                self.chooseLine.setChecked(True)
                self.setLayoutHidden(self.chosenTrafoFormLayout, True)
                self.setLayoutHidden(self.chosenLineFormLayout, False)
                self.trafoSubmitPushButton.setHidden(True)
                self.removeTrafoPushButton.setHidden(True)
                self.setLayoutHidden(self.ControlPanelLayout, True)
                self.removeTLPushButton.setHidden(False)
                self.updateLineModelOptions()
                self.updateLineInspector()
            elif isinstance(curve.obj, Transformer):
                # Show trafo inspect
                self.setLayoutHidden(self.InputNewLineType, True)
                self.hideSpacer()
                self.setLayoutHidden(self.BusLayout, True)
                self.setLayoutHidden(self.LineOrTrafoLayout, False)
                self.chooseTrafo.setChecked(True)
                self.setLayoutHidden(self.chosenTrafoFormLayout, False)
                self.setLayoutHidden(self.chosenLineFormLayout, True)
                self.trafoSubmitPushButton.setHidden(False)
                self.removeTrafoPushButton.setHidden(False)
                self.removeTLPushButton.setHidden(True)
                self.tlSubmitByModelPushButton.setHidden(True)
                self.tlSubmitByImpedancePushButton.setHidden(True)
                self.setLayoutHidden(self.ControlPanelLayout, True)
                self.updateTrafoInspector()
        else:
            # No element case
            self.setLayoutHidden(self.BusLayout, True)
            self.setLayoutHidden(self.LineOrTrafoLayout, True)
            self.setLayoutHidden(self.InputNewLineType, True)
            self.setLayoutHidden(self.ControlPanelLayout, True)
            self.showSpacer()

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
        coords = self._currElementCoords
        curve = self.getCurveFromGridPos(self._currElementCoords)
        if not isinstance(self.Scene.grid[coords], Bus) and not curve:
            bus = self.system.add_bus()
            self.Scene.grid[coords] = bus
            self.statusMsg.emit_sig('Added bus')
        else:
            self.Scene.removeItem(self.Scene.pixmap[coords])
            self.statusMsg.emit_sig('There\'s an element in this position!')

    def lineProcessing(self, mode):
        """
        Updates the line parameters based on Y and Z or parameters from LINE_TYPES,
        or converts a trafo into a line and update its parameters following
        Called by: tlSubmitByImpedancePushButton.pressed, tlSubmitByModelPushButton.pressed

        Parameters
        ----------
        mode: either 'parameters' or 'impedance'
        """
        curve = self.getCurveFromGridPos(self._currElementCoords)
        if isinstance(curve.obj, TransmissionLine):
            # The element already is a line
            line = curve.obj
            if mode == 'parameters':
                param_values = self.findParametersSetFromComboBox()
                # Current selected element is a line
                # Update using properties
                # Z and Y are obtained from the updated properties
                if param_values is not None:
                    ell = float(self.EllLineEdit.text()) * 1e3
                    vbase = float(self.VbaseLineEdit.text()) * 1e3
                    self.updateLineWithParameters(line, param_values, ell, vbase)
                    self.LayoutManager()
                    self.statusMsg.emit_sig('Updated line with parameters')
                else:
                    self.statusMsg.emit_sig('You have to choose a valid model')
            elif mode == 'impedance':
                # Current selected element is a line
                # Update using impedance and admittance
                R = float(self.TlRLineEdit.text()) / 100
                X = float(self.TlXLineEdit.text()) / 100
                Y = float(self.TlYLineEdit.text()) / 100
                Z = R + 1j * X
                Y = 1j * Y
                ell = float(self.EllLineEdit.text()) * 1e3
                vbase = float(self.VbaseLineEdit.text()) * 1e3
                self.updateLineWithImpedances(line, Z, Y, ell, vbase)
                self.LayoutManager()
                self.statusMsg.emit_sig('Update line with impedances')
        elif isinstance(curve.obj, Transformer):
            # The element is a trafo and will be converted into a line
            trafo = curve.obj
            self.remove_trafo(curve)
            new_line = TransmissionLine(orig=trafo.orig, dest=trafo.dest)
            if mode == 'parameters':
                param_values = self.findParametersSetFromComboBox()
                if param_values is not None:
                    ell = float(self.EllLineEdit.text()) * 1e3
                    vbase = float(self.VbaseLineEdit.text()) * 1e3
                    self.updateLineWithParameters(new_line, param_values, ell, vbase)
                    self.statusMsg.emit_sig('trafo -> line, updated with parameters')
                else:
                    self.statusMsg.emit_sig('You have to choose a valid model')
            elif mode == 'impedance':
                R = float(self.TlRLineEdit.text()) / 100
                X = float(self.TlXLineEdit.text()) / 100
                Y = float(self.TlYLineEdit.text()) / 100
                Z = R + 1j * X
                Y = 1j * Y
                ell = float(self.EllLineEdit.text()) * 1e3
                vbase = float(self.VbaseLineEdit.text()) * 1e3
                self.updateLineWithImpedances(new_line, Z, Y, ell, vbase)
                self.statusMsg.emit_sig('trafo -> line, updated with impedances')
            new_curve = LineSegment(obj=new_line,
                                    dlines=curve.dlines,
                                    coords=curve.coords)
            for line_drawing in new_curve.dlines:
                blue_pen = QPen()
                blue_pen.setColor(Qt.blue)
                blue_pen.setWidthF(2.5)
                line_drawing.setPen(blue_pen)
                self.Scene.addItem(line_drawing)
            self.add_line(new_curve)
            self.LayoutManager()

    def trafoProcessing(self):
        """
        Updates a trafo with the given parameters if the current element is a trafo
        or converts a line into a trafo with the inputted parameters
        Called by: trafoSubmitPushButton.pressed
        """
        curve = self.getCurveFromGridPos(self._currElementCoords)
        if isinstance(curve.obj, TransmissionLine):
            # Transform line into a trafo
            line = curve.obj
            self.remove_line(curve)
            new_trafo = Transformer(
                orig=line.orig,
                dest=line.dest,
                snom=float(self.SNomTrafoLineEdit.text()) * 1e6,
                jx0=float(self.XZeroSeqTrafoLineEdit.text()) / 100,
                jx1=float(self.XPosSeqTrafoLineEdit.text()) / 100,
                primary=SYMBOL_TO_PY[self.TrafoPrimary.currentText()],
                secondary=SYMBOL_TO_PY[self.TrafoSecondary.currentText()]
            )
            new_curve = LineSegment(obj=new_trafo,
                                    dlines=curve.dlines,
                                    coords=curve.coords)
            for line_drawing in new_curve.dlines:
                blue_pen = QPen()
                blue_pen.setColor(Qt.red)
                blue_pen.setWidthF(2.5)
                line_drawing.setPen(blue_pen)
                self.Scene.addItem(line_drawing)
            self.add_trafo(new_curve)
            self.LayoutManager()
            self.statusMsg.emit_sig('Line -> trafo')
        elif isinstance(curve.obj, Transformer):
            # Update parameters of selected trafo
            trafo = curve.obj
            trafo.snom = float(self.SNomTrafoLineEdit.text()) * 1e6
            trafo.jx0 = float(self.XZeroSeqTrafoLineEdit.text()) / 100
            trafo.jx1 = float(self.XPosSeqTrafoLineEdit.text()) / 100
            trafo.primary = SYMBOL_TO_PY[self.TrafoPrimary.currentText()]
            trafo.secondary = SYMBOL_TO_PY[self.TrafoSecondary.currentText()]
            self.LayoutManager()
            self.statusMsg.emit_sig('Updated trafo parameters')

    def remove_curve(self, curve=None):
        if curve is None:
            curve = self.getCurveFromGridPos(self._currElementCoords)
        for linedrawing in curve.dlines:
            self.Scene.removeItem(linedrawing)
        self.curves.remove(curve)

    def remove_trafo(self, curve=None):
        """Remove a trafo (draw and electrical representation)
        Parameters
        ----------
        curve: curve of trafo to be removed.
            If it is None, current selected trafo in interface will be removed
        """
        if curve is None:
            curve = self.getCurveFromGridPos(self._currElementCoords)
        self.remove_curve(curve)
        self.system.remove_trafo(curve.obj, tuple(curve.coords))
        self.statusMsg.emit_sig('Removed trafo')

    def remove_line(self, curve=None):
        """Remove a line (draw and electrical representation)

        Parameters
        ----------
        curve: curve of line to be removed.
            If it is None, current selected line in interface will be removed
        """
        if curve is None:
            curve = self.getCurveFromGridPos(self._currElementCoords)
        self.remove_curve(curve)
        self.system.remove_line(curve.obj, tuple(curve.coords))
        self.statusMsg.emit_sig('Removed line')

    def removeElementsLinked2Bus(self, bus):
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
        coords = self._currElementCoords
        bus = self.getBusFromGridPos(coords)
        if bus:
            self.removeElementsLinked2Bus(bus)
            n = self.system.id2n(bus.bus_id)
            self.system.remove_bus(n)
            self.Scene.removeItem(self.Scene.pixmap[coords])
            self.Scene.pixmap[coords] = 0
            self.Scene.grid[coords] = 0

    def add_gen(self):
        """Adds generation to the bus, make some QLineEdits activated
        Called by: AddGenerationButton.pressed (__init__)
        """
        bus = self.getBusFromGridPos(self._currElementCoords)
        self.BusV_Value.setEnabled(True)
        self.XdLineEdit.setEnabled(True)
        if bus.bus_id > 0:
            self.PgInput.setEnabled(True)
        self.GenGround.setEnabled(True)
        self.AddGenerationButton.setText('OK')
        self.statusMsg.emit_sig('Input generation data...')
        self.AddGenerationButton.disconnect()
        self.AddGenerationButton.pressed.connect(self.submit_gen)

    def submit_gen(self):
        """Updates bus parameters with the user input in bus inspector
        Called by: AddedGenerationButton.pressed (add_gen)
        """
        coords = self._currElementCoords
        if isinstance(self.Scene.grid[coords], Bus):
            bus = self.getBusFromGridPos(coords)
            bus.v = float(self.BusV_Value.text())
            bus.pg = float(self.PgInput.text()) / 100
            bus.gen_ground = self.GenGround.isChecked()
            if self.XdLineEdit.text() == '\u221E':
                bus.xd = np.inf
            else:
                bus.xd = float(self.XdLineEdit.text()) / 100
            self.BusV_Value.setEnabled(False)
            self.PgInput.setEnabled(False)
            self.XdLineEdit.setEnabled(False)
            self.GenGround.setEnabled(False)
            self.AddGenerationButton.disconnect()
            if bus.bus_id > 0:
                self.AddGenerationButton.setText('-')
                self.AddGenerationButton.pressed.connect(self.remove_gen)
            else:
                self.AddGenerationButton.setText('EDIT')
                self.AddGenerationButton.pressed.connect(self.add_gen)
            self.statusMsg.emit_sig('Added generation')

    def remove_gen(self):
        """
        Called by: AddGenerationButton.pressed (submit_gen)
        """
        coords = self._currElementCoords
        if isinstance(self.Scene.grid[coords], Bus):
            bus = self.getBusFromGridPos(coords)
            bus.v = 1
            bus.pg = 0
            bus.xd = np.inf
            bus.gen_ground = False
            self.updateBusInspector(bus)
            self.AddGenerationButton.setText('+')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.add_gen)
            self.statusMsg.emit_sig('Removed generation')

    def add_load(self):
        """
        Called by: AddLoadButton.pressed (__init__)
        """
        self.PlInput.setEnabled(True)
        self.QlInput.setEnabled(True)
        self.LoadGround.setEnabled(True)
        self.AddLoadButton.setText('OK')
        self.statusMsg.emit_sig('Input load data...')
        self.AddLoadButton.disconnect()
        self.AddLoadButton.pressed.connect(self.submit_load)

    def submit_load(self):
        """
        Called by: AddLoadButton.pressed (add_load)
        """
        coords = self._currElementCoords
        if isinstance(self.Scene.grid[coords], Bus):
            bus = self.getBusFromGridPos(coords)
            bus.pl = float(self.PlInput.text()) / 100
            bus.ql = float(self.QlInput.text()) / 100
            bus.load_ground = SYMBOL_TO_PY[self.LoadGround.currentText()]
            self.PlInput.setEnabled(False)
            self.QlInput.setEnabled(False)
            self.LoadGround.setEnabled(False)
            self.AddLoadButton.setText('-')
            self.AddLoadButton.disconnect()
            self.AddLoadButton.pressed.connect(self.remove_load)
            self.statusMsg.emit_sig('Added load')

    def remove_load(self):
        """
        Called by: AddLoadButton.pressed (submit_load)
        """
        coords = self._currElementCoords
        if isinstance(self.Scene.grid[coords], Bus):
            bus = self.getBusFromGridPos(coords)
            bus.pl = 0
            bus.ql = 0
            bus.load_ground = EARTH
            self.updateBusInspector(bus)
            self.AddLoadButton.setText('+')
            self.AddLoadButton.disconnect()
            self.AddLoadButton.pressed.connect(self.add_load)
            self.statusMsg.emit_sig('Removed load')

    def doAfterMouseRelease(self):
        """
        If line's bool remove is True, the line will be removed.
        The remove may have three causes:
        1. The line crossed with itself or with another line
        2. The line was inputted with only two points
        3. The line has not a destination bus
        """
        if self.curves:
            curr_curve = self.curves[-1]
            curr_curve.remove |= (len(curr_curve.coords) <= 2
                                  or curr_curve.obj.dest is None
                                  or curr_curve.obj.dest == curr_curve.obj.orig)
            if not self._startNewTL and not curr_curve.remove:
                self.system.add_line(self.curves[-1].obj, tuple(self.curves[-1].coords))
            self._startNewTL = True
            if curr_curve.remove:
                self.remove_curve(curr_curve)
            for curve in self.curves:
                assert curve.obj.orig is not None
                assert curve.obj.dest is not None
                assert curve.obj.dest != curve.obj.orig

        self.system.update(Nmax=self.nmax)
        self.LayoutManager()


class Software(QMainWindow):
    def __init__(self):
        super(Software, self).__init__()
        # Central widget
        self.circuit = CircuitInputer()
        self.circuit.statusMsg.signal.connect(lambda args: self.displayStatusMsg(args))
        self.setCentralWidget(self.circuit)

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

        loadAct = QAction('Open session', self)
        loadAct.setShortcut('Ctrl+O')
        loadAct.triggered.connect(self.loadSession)

        createReport = QAction('Generate report', self)
        createReport.setShortcut('Ctrl+R')
        createReport.triggered.connect(self.report)

        addLineAct = QAction('Add line type', self)
        addLineAct.setShortcut('Ctrl+L')
        addLineAct.triggered.connect(self.addLineType)

        editLineAct = QAction('Edit line type', self)
        editLineAct.triggered.connect(self.editLineType)

        configure_simulation = QAction('Configure simulation', self)
        configure_simulation.setShortcut('Ctrl+X')
        configure_simulation.triggered.connect(self.configureSimulation)

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

        settings = menubar.addMenu('S&ettings')
        settings.addAction(configure_simulation)

        self.setWindowTitle(NAME)
        self.setGeometry(50, 50, 1000, 600)
        self.setMinimumWidth(1000)
        self.show()

    def configureSimulation(self):
        self.circuit.setLayoutHidden(self.circuit.BusLayout, True)
        self.circuit.setLayoutHidden(self.circuit.LineOrTrafoLayout, True)
        self.circuit.setLayoutHidden(self.circuit.ControlPanelLayout, False)
        self.circuit.updateNmaxSlider(self.circuit.nmax)
        self.circuit.updateNmaxLabel(self.circuit.nmax)

    def displayStatusMsg(self, args):
        self.statusBar().showMessage(args)

    def saveSession(self):
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
                self.storeData(file)
                file.close()

    def loadSession(self):
        self.startNewSession()
        sessions_dir = getSessionsDir()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(parent=self,
                                                  caption="Load Session",
                                                  directory=sessions_dir,
                                                  filter="All Files (*)",
                                                  options=options)
        if filename:
            with open(filename, 'br') as file:
                self.createLocalData(file)
                file.close()
            self.createSchematic(self.circuit.Scene)

    def report(self):
        sessions_dir = getSessionsDir()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(parent=self,
                                                  caption="Save Report",
                                                  directory=sessions_dir,
                                                  filter="PDF Files (*.pdf)",
                                                  options=options)
        if filename:
            create_report(self.circuit.system, self.circuit.curves, self.circuit.Scene.grid, filename)

    def addLineType(self):
        self.circuit.setLayoutHidden(self.circuit.InputNewLineType, False)
        self.circuit.setLayoutHidden(self.circuit.BusLayout, True)
        self.circuit.setLayoutHidden(self.circuit.LineOrTrafoLayout, True)
        self.displayStatusMsg('Adding new line model')

    def editLineType(self):
        self.displayStatusMsg("Editing line types is currently not implemented!")
        raise NotImplementedError

    def startNewSession(self):
        self.clear_interface()
        self.reset_system_state_variables()
        self.circuit.doAfterMouseRelease()

    def clear_interface(self):
        to_remove = len(self.circuit.curves)
        for i in range(to_remove):
            self.circuit.remove_curve(self.circuit.curves[0])
        N = self.circuit.Scene.N
        for i in range(N):
            for j in range(N):
                if isinstance(self.circuit.Scene.grid[i, j], Bus):
                    self.circuit.Scene.removeItem(self.circuit.Scene.pixmap[i, j])

    def reset_system_state_variables(self):
        N = self.circuit.Scene.N
        self.circuit.system = PowerSystem()
        self.circuit.curves = []
        self.circuit.Scene.grid = np.zeros((N, N), object)
        self.circuit.Scene.pixmap = np.zeros((N, N), object)

    def createLocalData(self, file):
        db = pickle.load(file)
        self.circuit.system = db['SYSTEM']
        self.circuit.curves = db['CURVES']
        self.circuit.line_types = db['LINE_TYPES']
        self.circuit.Scene.grid = db['GRID']
        for bus in self.circuit.system.buses:
            assert bus in self.circuit.Scene.grid
        for curve in self.circuit.curves:
            assert curve.obj in self.circuit.system.lines or curve.obj in self.circuit.system.trafos

    def storeData(self, file):
        filtered_curves = []
        for curve in self.circuit.curves:
            filtered_curves.append(LineSegment(obj=curve.obj,
                                               coords=curve.coords,
                                               dlines=[]))
        db = {'SYSTEM': self.circuit.system,
              'CURVES': filtered_curves,
              'LINE_TYPES': self.circuit.line_types,
              'GRID': self.circuit.Scene.grid}
        pickle.dump(db, file)
        return db

    def createSchematic(self, scene):
        squarel = scene.oneSquareSideLength
        for i in range(scene.N):
            for j in range(scene.N):
                if isinstance(scene.grid[i, j], Bus):
                    point = (squarel / 2 + squarel * j,
                             squarel / 2 + squarel * i)
                    drawbus = scene.drawBus(point)
                    scene.pixmap[i, j] = drawbus
        for curve in self.circuit.curves:
            for pairs in interface_coordpairs(curve.coords, squarel):
                if isinstance(curve.obj, TransmissionLine):
                    dline = scene.drawLine(pairs, color='b')
                else:
                    dline = scene.drawLine(pairs, color='r')
                curve.dlines.append(dline)


def main():
    app = QApplication(sys.argv)
    Software()
    sys.exit(app.exec_())
