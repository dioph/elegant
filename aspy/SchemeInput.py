import shelve
import logging
import sys
import traceback
import glob
import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from aspy.core import *

"""
# ---------------------------------------------------------------------------------------------------------

# The global variables are being used to specify the current state of the system    

# ---------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------

# N: graphical grid dimension (N x N - used to initializate the SchemeInputer class)

# ---------------------------------------------------------------------------------------------------------

# GRID_BUSES: N X N numpy array that holds core.aspy.Barra elements. It is used 
# to link the SchemeInput graphical interface to the data arrays manipulation

# ---------------------------------------------------------------------------------------------------------

# BUSES_PIXMAP: N x N numpy array that holds PyQt5.QtGui.QPixMap items representing
# the buses drawings on SchemeInputer

# ---------------------------------------------------------------------------------------------------------

# BUSES: numpy array that holds core.aspy.Barra elements. Each element has the following
# form: [aspy.core.Barra Bus]

# ---------------------------------------------------------------------------------------------------------

# TL: list that holds transmission line elements. Each element has the following form:
# [[aspy.core.LT lines, [PyQt5.QtWidgets.QGraphicsLineItem dlines], [tuple coordinates], bool remove]]

# ---------------------------------------------------------------------------------------------------------

# TRANSFORMERS: list that holds transformer elements. Each element has the following form:
# [[aspy.core.Trafo], [PyQt5.QtWidgets.QGraphicsLineItem dlines], [tuple coordinates]]

# ---------------------------------------------------------------------------------------------------------

# LINE_TYPES: dictionaries that holds the line parameters to be put into lines

# ---------------------------------------------------------------------------------------------------------
"""

N = 20
ID = 1
GRID_BUSES = np.zeros((N, N), object)
BUSES_PIXMAP = np.zeros((N, N), object)
BUSES = []
TL = []
TRANSFORMERS = []
LINE_TYPES = [['Default', {'r': 1.0, 'd12': 2.0, 'd23': 2.0, 'd31': 2.0, 'd': 1.0, 'rho': 1.78e-8, 'm': 1.0}]]

class GenericSignal(QObject):
    signal = pyqtSignal(object)

    def __init__(self, *args):
        super(GenericSignal, self).__init__()
        self.emit_sig(args)

    def emit_sig(self, args):
        self.signal.emit(args)


class SchemeInputer(QGraphicsScene):
    def __init__(self, n=N, length=50, *args, **kwargs):
        super(SchemeInputer, self).__init__(*args, **kwargs)
        self.n = n
        self._oneUnityLength = length
        self._moveHistory = np.ones((2, 2))*-1
        self._selectorHistory = np.array([None, -1, -1])  # 0: old QRect, 1 & 2: coordinates to new QRect
        self._lastRetainer, self._firstRetainer = False, True
        self._pointerSignal = GenericSignal()
        self._methodSignal = GenericSignal()
        self._dataSignal = GenericSignal()
        self.selector_radius = length/2
        self.setSceneRect(0, 0, self._oneUnityLength*self.n, self._oneUnityLength*self.n)  # Visible portion of Scene to View
        self.quantizedInterface = self.getQuantizedInterface()
        self.showQuantizedInterface()
        self.setSceneRect(-2*self._oneUnityLength, -2*self._oneUnityLength, self._oneUnityLength*(self.n+4), self._oneUnityLength*(self.n+4))


    @staticmethod
    def distance(interface_point, point):
        return np.sqrt((interface_point[0]-point.x())**2+(interface_point[1]-point.y())**2)


    def Point_pos(self, central_point):
        """Returns point coordinates in grid
        """
        i = int((central_point.y()-self._oneUnityLength/2)/self._oneUnityLength)
        j = int((central_point.x()-self._oneUnityLength/2)/self._oneUnityLength)
        return i, j


    def mouseReleaseEvent(self, event):
        self._moveHistory[:, :] = -1
        self._lastRetainer = False
        self._firstRetainer = True
        self._methodSignal.emit_sig('mouseReleased')


    def drawLine(self, coordinates):
        pen = QPen()
        pen.setWidth(2.5)
        pen.setColor(Qt.blue)
        line = self.addLine(coordinates[0, 0], coordinates[0, 1], coordinates[1, 0], coordinates[1, 1], pen)
        print(type(line))
        return line


    def crossCursorPositioning(self):
        pass


    def dropEvent(self, event):
        pass


    def drawSquare(self, coordinates):
        pen = QPen()
        pen.setColor(Qt.yellow)
        brush = QBrush()
        brush.setColor(Qt.yellow)
        brush.setStyle(Qt.Dense7Pattern)
        x, y = coordinates
        QRect = self.addRect(x, y, self._oneUnityLength, self._oneUnityLength, pen, brush)
        return QRect


    def clearSquare(self, oldQRect):
        # TODO bug in clearing square after scrolling in any direction
        if oldQRect is not None:
            self.removeItem(oldQRect)


    def mouseDoubleClickEvent(self, event):
        global BUSES_PIXMAP
        try:
            double_pressed = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                if self.distance(double_pressed, central_point) <= self.selector_radius:
                    i, j = self.Point_pos(central_point)
                    self._pointerSignal.emit_sig((i, j))
                    self._methodSignal.emit_sig('addBus')
                    pixmap = QPixmap('./data/icons/DOT.jpg')
                    pixmap = pixmap.scaled(self._oneUnityLength, self._oneUnityLength, Qt.KeepAspectRatio)
                    sceneItem = self.addPixmap(pixmap)
                    pixmap_COORDS = central_point.x()-self._oneUnityLength/2, central_point.y()-self._oneUnityLength/2
                    sceneItem.setPos(pixmap_COORDS[0], pixmap_COORDS[1])
                    BUSES_PIXMAP[(i, j)] = sceneItem
        except Exception:
            logging.error(traceback.format_exc())


    def mousePressEvent(self, event):
        # L button: 1; R button: 2
        try:
            if event.button() in (1, 2):
                pressed = event.scenePos().x(), event.scenePos().y()
                for central_point in self.quantizedInterface.flatten():
                    if self.distance(pressed, central_point) <= self.selector_radius:
                        i, j = self.Point_pos(central_point)
                        self.clearSquare(self._selectorHistory[0])
                        #  up-right corner is (0, 0)
                        self._selectorHistory[1] = central_point.x() - self._oneUnityLength/2
                        self._selectorHistory[2] = central_point.y() - self._oneUnityLength/2
                        self._selectorHistory[0] = self.drawSquare(self._selectorHistory[1:])
                        self._pointerSignal.emit_sig((i, j))
                        self._methodSignal.emit_sig('storeOriginAddLt')
                        self._methodSignal.emit_sig('LayoutManager')
        except Exception:
            logging.error(traceback.format_exc())


    def sceneRectChanged(self, QRectF):
        pass


    def mouseMoveEvent(self, event):
        """This method gives behavior to wire tool"""
        if event.button() == 0:
            clicked = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                i, j = self.Point_pos(central_point)
                try:
                    if self.distance(clicked, central_point) <= self.selector_radius:
                        if np.all(self._moveHistory[0] < 0):  # Set source
                            self._moveHistory[0, 0] = central_point.x(); self._moveHistory[0, 1] = central_point.y()
                            if isinstance(GRID_BUSES[i, j], Barra):  # Asserts the start was from a bus
                                self._firstRetainer = False
                        if central_point.x() != self._moveHistory[0, 0] \
                                or central_point.y() != self._moveHistory[0, 1]:  # Set destiny
                            self._moveHistory[1, 0] = central_point.x(); self._moveHistory[1, 1] = central_point.y()
                        if (np.all(self._moveHistory > 0)) and \
                                (np.any(self._moveHistory[0, :] != np.any(self._moveHistory[1, :]))):
                            ### DRAW LINE ###
                            try:
                                if isinstance(GRID_BUSES[i, j], Barra) and not self._firstRetainer:
                                    # when a bus is achieved
                                    line = self.drawLine(self._moveHistory)
                                    self._moveHistory[:, :] = -1
                                    self._lastRetainer = True  # Prevent the user for put line outside last bus
                                    self._pointerSignal.emit_sig((i, j))
                                    self._dataSignal.emit_sig(line)
                                    self._methodSignal.emit_sig('addLine')
                                elif not isinstance(GRID_BUSES[i, j], Barra) and not (self._lastRetainer or self._firstRetainer):
                                    # started from a bus
                                    line = self.drawLine(self._moveHistory)
                                    self._moveHistory[:, :] = -1
                                    self._pointerSignal.emit_sig((i, j))
                                    self._dataSignal.emit_sig(line)
                                    self._methodSignal.emit_sig('addLine')
                            except Exception:
                                logging.error(traceback.format_exc())
                    else:  # No bar case
                        pass
                except Exception:
                    logging.error(traceback.format_exc())


    def getQuantizedInterface(self):
        quantizedInterface = np.zeros((self.n, self.n), tuple)
        width, height = self.width(), self.height()
        for i in range(self.n):
            for j in range(self.n):
                quantizedInterface[i, j] = \
                    QPoint(width/(2*self.n) + i*width/self.n, height/(2*self.n) + j*height/self.n)
        return quantizedInterface


    def showQuantizedInterface(self):
        #  (0, 0) is upper left corner
        width, height = self.width(), self.height()
        spacing_x, spacing_y = width/self.n, height/self.n
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


    def drawCrossCursor(self):
        pass


class CircuitInputer(QWidget):
    def __init__(self, parent=None):
        ### ========================= General initializations ======================= ###
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
        self.__calls = {'addBus': self.add_bus,
                        'addLine': self.add_line,
                        'LayoutManager': self.LayoutManager,
                        'mouseReleased': self.doAfterMouseRelease,
                        'storeOriginAddLt': self.storeOriginAddLt}
        self.Scene._pointerSignal.signal.connect(lambda args: self.setCurrentObject(args))
        self.Scene._dataSignal.signal.connect(lambda args: self.settemp(args))
        self.Scene._methodSignal.signal.connect(lambda args: self.methodsTrigger(args))

        ### ========================= Inspectors =================================== ###
        self.InspectorLayout = QVBoxLayout()

        ## Layout for general bar case ###
        self.BarLayout = QVBoxLayout()

        ### Bus title ###
        # TODO add X'd in each bus
        self.BarTitle = QLabel('Bar title')
        self.BarTitle.setAlignment(Qt.AlignCenter)
        self.BarTitle.setMinimumWidth(200)

        ### Bus voltage ###
        self.BarV_Value = QLineEdit('0.0')
        self.BarV_Value.setEnabled(False)
        self.BarV_Value.setValidator(QDoubleValidator(0.0, 100.0, 2))

        ### Bus angle ###
        self.BarAngle_Value = QLineEdit('0.0º')
        self.BarAngle_Value.setEnabled(False)

        ### FormLayout to hold bus data ###
        self.BarDataFormLayout = QFormLayout()

        ### Adding bus voltage and bus angle to bus data FormLayout ###
        self.BarDataFormLayout.addRow('|V|', self.BarV_Value)
        self.BarDataFormLayout.addRow('\u03b4', self.BarAngle_Value)

        ### Label with 'Geração' ###
        self.AddGenerationLabel = QLabel('Geração')
        self.AddGenerationLabel.setAlignment(Qt.AlignCenter)

        ### Button to add generation ###
        self.AddGenerationButton = QPushButton('+')
        self.AddGenerationButton.pressed.connect(self.add_gen)  # Bind button to make input editable

        ### FormLayout to add generation section ###
        self.AddGenerationFormLayout = QFormLayout()
        self.AddLoadFormLayout = QFormLayout()

        ### Line edit to Xd bus ###
        self.XdLineEdit = QLineEdit('0.0'); self.XdLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.XdLineEdit.setEnabled(False)

        ### Line edit to input bus Pg ###
        self.PgInput = QLineEdit('0.0'); self.PgInput.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.PgInput.setEnabled(False)

        ### Line edit to input bus Qg ###
        self.QgInput = QLineEdit('0.0'); self.QgInput.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.QgInput.setEnabled(False)

        ### Adding Pg, Qg to add generation FormLayout ###
        self.AddGenerationFormLayout.addRow('X\'d', self.XdLineEdit)
        self.AddGenerationFormLayout.addRow('Qg', self.QgInput)
        self.AddGenerationFormLayout.addRow('Pg', self.PgInput)

        ### Label with 'Carga' ###
        self.AddLoadLabel = QLabel('Carga')
        self.AddLoadLabel.setAlignment(Qt.AlignCenter)

        ### PushButton that binds to three different methods ###
        self.AddLoadButton = QPushButton('+')
        self.AddLoadButton.pressed.connect(self.add_load)

        ### LineEdit with Ql, Pl ###
        self.QlInput = QLineEdit('0.0'); self.QlInput.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.PlInput = QLineEdit('0.0'); self.PlInput.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.PlInput.setEnabled(False); self.QlInput.setEnabled(False)

        ### Adding Pl and Ql to add load FormLayout ###
        self.AddLoadFormLayout.addRow('Ql ', self.QlInput)
        self.AddLoadFormLayout.addRow('Pl ', self.PlInput)
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

        ### Layout for input new type of line ###
        self.InputNewLineType = QVBoxLayout()
        self.InputNewLineTypeFormLayout = QFormLayout()

        self.ModelName = QLineEdit(); self.ModelName.setValidator(QRegExpValidator(QRegExp("[A-Za-z]*")))
        self.RhoLineEdit = QLineEdit()
        self.RhoLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        # self.EllLineEdit = QLineEdit()
        # self.EllLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.rLineEdit = QLineEdit()
        self.rLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.d12LineEdit = QLineEdit()
        self.d12LineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.d23LineEdit = QLineEdit()
        self.d23LineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.d31LineEdit = QLineEdit()
        self.d31LineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.dLineEdit = QLineEdit()
        self.dLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.mLineEdit = QLineEdit()
        self.mLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))

        self.InputNewLineTypeFormLayout.addRow('Name', self.ModelName)
        self.InputNewLineTypeFormLayout.addRow('rho', self.RhoLineEdit)
        # self.InputNewLineTypeFormLayout.addRow('l', self.EllLineEdit)
        self.InputNewLineTypeFormLayout.addRow('r', self.rLineEdit)
        self.InputNewLineTypeFormLayout.addRow('d12', self.d12LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d23', self.d23LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d31', self.d31LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d', self.dLineEdit)
        self.InputNewLineTypeFormLayout.addRow('m', self.mLineEdit)
        self.mLineEdit.setValidator(QIntValidator(1, 4))

        self.InputNewLineType.addStretch()
        self.InputNewLineType.addLayout(self.InputNewLineTypeFormLayout)
        self.SubmitNewLineTypePushButton = QPushButton('Submit')
        self.SubmitNewLineTypePushButton.setMinimumWidth(200.0)
        self.SubmitNewLineTypePushButton.pressed.connect(self.addNewLineType)
        self.InputNewLineType.addWidget(self.SubmitNewLineTypePushButton)
        self.InputNewLineType.addStretch()

        ### General Layout for LT case ###
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
        self.EllLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))

        imp_expr_val = QRegExp("^\d{1,3}\.\d{1,3}[+,-]\d{1,3}\.\d{1,3}\j$")
        self.LtZLineEdit = QLineEdit()
        self.LtZLineEdit.setValidator(QRegExpValidator(imp_expr_val))
        # self.LtZLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))

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
        self.choosedLtFormLayout.addRow('l', self.EllLineEdit)
        self.choosedLtFormLayout.addRow('Z', self.LtZLineEdit)
        self.choosedLtFormLayout.addRow('Y', self.LtYLineEdit)

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
        self.SNomTrafoLineEdit = QLineEdit(); self.SNomTrafoLineEdit.setValidator(QDoubleValidator(0, 10.0, 2))
        self.XZeroSeqTrafoLineEdit = QLineEdit(); self.XZeroSeqTrafoLineEdit.setValidator(QDoubleValidator(0, 10.0, 2))
        self.XPosSeqTrafoLineEdit = QLineEdit(); self.XPosSeqTrafoLineEdit.setValidator(QDoubleValidator(0, 10.0, 2))
        self.VNom1LineEdit = QLineEdit(); self.VNom1LineEdit.setValidator(QDoubleValidator(0, 10.0, 2))
        self.VNom2LineEdit = QLineEdit(); self.VNom2LineEdit.setValidator(QDoubleValidator(0, 10.0, 2))
        self.TrafoConnection = QComboBox()
        self.TrafoConnection.addItem('gYyg')
        self.TrafoConnection.addItem('gY\u0394')
        self.TrafoConnection.addItem('gYy')

        self.trafoSubmitPushButton = QPushButton('Submit trafo')
        self.trafoSubmitPushButton.pressed.connect(self.trafoProcessing)
        self.trafoSubmitPushButton.setMinimumWidth(200)

        self.removeTrafoPushButton = QPushButton('Remove trafo')
        self.removeTrafoPushButton.pressed.connect(self.remove_selected_trafo)
        """" 
        # Reason of direct button bind to self.LayoutManager: 
        #     The layout should disappear only when a line or trafo is excluded.
        #     The conversion trafo <-> line calls the method remove_selected_(line/trafo)
        """
        self.removeTrafoPushButton.pressed.connect(self.LayoutManager)
        self.removeTrafoPushButton.setMinimumWidth(200)

        self.choosedTrafoFormLayout.addRow('Snom', self.SNomTrafoLineEdit)
        self.choosedTrafoFormLayout.addRow('X0', self.XZeroSeqTrafoLineEdit)
        self.choosedTrafoFormLayout.addRow('X+', self.XPosSeqTrafoLineEdit)
        self.choosedTrafoFormLayout.addRow('VNom 1', self.VNom1LineEdit)
        self.choosedTrafoFormLayout.addRow('VNom 2', self.VNom2LineEdit)
        self.choosedTrafoFormLayout.addRow('Lig.', self.TrafoConnection)

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

        ### Layout that holds bus inspector and Stretches ###
        self.InspectorAreaLayout = QVBoxLayout()
        self.InspectorLayout.addStretch()
        self.InspectorLayout.addLayout(self.BarLayout)
        self.InspectorLayout.addLayout(self.LtOrTrafoLayout)
        self.InspectorLayout.addStretch()
        self.InspectorAreaLayout.addLayout(self.InspectorLayout)

        ### Toplayout ###
        self.TopLayout = QHBoxLayout()
        self.Spacer = QSpacerItem(200, 0, 0, 0)
        self.TopLayout.addItem(self.Spacer)
        self.TopLayout.addLayout(self.InspectorAreaLayout)
        self.TopLayout.addLayout(self.SchemeInputLayout)
        self.TopLayout.addLayout(self.InputNewLineType)
        self.setLayout(self.TopLayout)

        ### All layouts hidden at first moment ###
        self.setLayoutHidden(self.BarLayout, True)
        self.setLayoutHidden(self.LtOrTrafoLayout, True)
        self.setLayoutHidden(self.InputNewLineType, True)
        self.showSpacer()


    def defineLtOrTrafoVisibility(self):
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
        try:
            if self.getTrafoFromGridPos(self._currElementCoords) is not None:
                TRAFO = self.getTrafoFromGridPos(self._currElementCoords)
                trafo = TRAFO[0]
                self.SNomTrafoLineEdit.setText('{:.2g}'.format(trafo.snom))
                self.XZeroSeqTrafoLineEdit.setText('{:.2g}'.format(trafo.jx0))
                self.XPosSeqTrafoLineEdit.setText('{:.2g}'.format(trafo.jx1))
                self.VNom1LineEdit.setText('{:.2g}'.format(trafo.vnom1))
                self.VNom2LineEdit.setText('{:.2g}'.format(trafo.vnom2))
                self.TrafoConnection.setCurrentText(trafo.connection)
            else:
                self.SNomTrafoLineEdit.setText('0.0')
                self.XZeroSeqTrafoLineEdit.setText('0.0')
                self.XPosSeqTrafoLineEdit.setText('0.0')
                self.VNom1LineEdit.setText('0.0')
                self.VNom2LineEdit.setText('0.0')
                self.TrafoConnection.setCurrentText('-')
        except Exception:
            logging.error(traceback.format_exc())



    def updateLtInspector(self):
        '''Updates the line inspector
        --------------------------------------------
        Called by: LayoutManager, lineProcessing
        --------------------------------------------
        '''
        try:
            LINE = self.getLtFromGridPos(self._currElementCoords)
            line = LINE[0]
            line_model = self.findParametersSetFromLt(line)
            self.EllLineEdit.setText('{:.03g}'.format(line.l))
            self.LtYLineEdit.setText('{number.imag:.03e}j'.format(number=line.Y))
            self.LtZLineEdit.setText('{number.real:.03g}{sgn}{number.imag:.03g}j'.\
                                     format(number=line.Z, sgn='+' if np.sign(line.Z.imag)>0 else ''))
            self.chooseLtModel.setCurrentText(line_model)
        except Exception:
            logging.error(traceback.format_exc())


    @staticmethod
    def findParametersSetFromLt(LINE):
        """Returns the name of parameters set of a existent line or
           returns None if the line has been set by impedance and admittance
        ---------------------------------------------------------------------
        """
        try:
            line_parameters_val = list(LINE.__dict__.values())[:8]
            if all(line_parameters_val == np.ones((8,)) * -1):
                return "No model"
            else:
                for line_type in LINE_TYPES:
                    if all(tuple(LINE.__getattribute__(key) == line_type[1].get(key) for key in line_type[1].keys())):
                        return line_type[0]
                    else:
                        continue
                return "No model"
        except Exception:
            logging.error(traceback.format_exc())


    def findParametersSetFromComboBox(self):
        """Find parameters set based on current selection of line or trafo inspector combo box
           If the line was set with parameters, returns 'None'
        ---------------------------------------------------------------------------------------
        """
        set_name = self.chooseLtModel.currentText()
        for line_types in LINE_TYPES:
            if set_name == line_types[0]:
                return line_types[1]
            else:
                continue
        return None


    def updateLtModelOptions(self):
        """Add the name of a new parameter set to QComboBox choose model,
           if the Combo has not the model yet
        -----------------------------------------------------------------
        """
        for line_type in LINE_TYPES:
            if self.chooseLtModel.isVisible() and self.chooseLtModel.findText(line_type[0]) < 0:
                self.chooseLtModel.addItem(line_type[0])
            else:
                pass


    def lineProcessing(self, mode):
        """
        --------------------------------------------------------------------------
        Updates the line parameters based on Y and Z or parameters from LINE_TYPES
        or converts a trafo into a line and update its parameters in follow
        -------------------------------------------------------------------------------
        Called by: line and trafo -> QPushButtons submit by model, submit by parameters
        -------------------------------------------------------------------------------
        """
        try:
            if self.getLtFromGridPos(self._currElementCoords) is not None:
                # The element already is a line
                assert(self.getTrafoFromGridPos(self._currElementCoords) is None)
                LINE = self.getLtFromGridPos(self._currElementCoords)
                line = LINE[0]
                if mode == 'parameters':
                    param_values = self.findParametersSetFromComboBox()
                    # Current selected element is a line
                    # Update using properties
                    # Z and Y are obttained from the updated properties
                    if param_values is not None:
                        l = float(self.EllLineEdit.text())
                        self.updateLineWithParameters(line, param_values, l)
                        self.LayoutManager()
                    else:
                        self._statusMsg.emit_sig('You have to choose an valid model')
                elif mode == 'impedance':
                    # Current selected element is a line
                    # Update using impedance and admittance
                    Z, Y = complex(self.LtZLineEdit.text()), complex(self.LtYLineEdit.text())
                    l = float(self.EllLineEdit.text())
                    self.updateLineWithImpedances(line, Z, Y, l)
                    self.LayoutManager()
            elif self.getTrafoFromGridPos(self._currElementCoords) is not None:
                # The element is a trafo and will be converted into a line
                assert(self.getLtFromGridPos(self._currElementCoords) is None)
                TRAFO = self.getTrafoFromGridPos(self._currElementCoords)
                self.remove_selected_trafo(TRAFO)
                new_line = LT(); new_line.origin = TRAFO[0].origin; new_line.destiny = TRAFO[0].destiny
                if mode == 'parameters':
                    param_values = self.findParametersSetFromComboBox()
                    if param_values is not None:
                        l = float(self.EllLineEdit.text())
                        self.updateLineWithParameters(new_line, param_values, l)
                    else:
                        self._statusMsg.emit_sig('You have to choose an valid model')
                elif mode == 'impedance':
                    Z, Y = complex(self.LtZLineEdit.text()), complex(self.LtYLineEdit.text())
                    l = float(self.EllLineEdit.text())
                    self.updateLineWithImpedances(new_line, Z, Y, l)
                inserting_line = [new_line, TRAFO[1], TRAFO[2], False]
                for line_drawing in inserting_line[1]:
                    blue_pen = QPen()
                    blue_pen.setColor(Qt.blue)
                    blue_pen.setWidth(2.5)
                    line_drawing.setPen(blue_pen)
                    self.Scene.addItem(line_drawing)
                TL.append(inserting_line)
                self.LayoutManager()
        except Exception:
            logging.error(traceback.format_exc())


    @staticmethod
    def updateLineWithParameters(line, param_values, l):
        line.Z, line.Y = None, None
        line.l = l
        line.__dict__.update(param_values)


    @staticmethod
    def updateLineWithImpedances(line, Z, Y, l):
        line.Z, line.Y = Z, Y
        line.l = l
        for key in list(line.__dict__.keys())[:8]:
            if key is not 'l':
                line.__setattr__(key, -1)


    def trafoProcessing(self):
        """
        --------------------------------------------------------------------------------------
        Updates a trafo with the given parameters if the current element is a trafo
        or converts a line into a trafo with the inputted parameters
        ---------------------------------------------------------------------------------------
        Called by: QPushButton Submit trafo
        ---------------------------------------------------------------------------------------
        """
        global TRANSFORMERS
        try:
            if self.getLtFromGridPos(self._currElementCoords) is not None:
                # Transform line into a trafo
                assert(self.getTrafoFromGridPos(self._currElementCoords) is None)
                line = self.getLtFromGridPos(self._currElementCoords)
                self.remove_selected_line(line)
                new_trafo = Trafo(
                                  snom=float(self.SNomTrafoLineEdit.text()),
                                  vnom1=float(self.VNom1LineEdit.text()),
                                  vnom2=float(self.VNom2LineEdit.text()),
                                  jx0=float(self.XZeroSeqTrafoLineEdit.text()),
                                  jx1=float(self.XPosSeqTrafoLineEdit.text()),
                                  connection=self.TrafoConnection.currentText(),
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
            elif self.getTrafoFromGridPos(self._currElementCoords) is not None:
                # Update parameters of selected trafo
                assert(self.getLtFromGridPos(self._currElementCoords) is None)
                trafo = self.getTrafoFromGridPos(self._currElementCoords)
                trafo[0].snom = float(self.SNomTrafoLineEdit.text())
                trafo[0].vnom1 = float(self.VNom1LineEdit.text())
                trafo[0].vnom2 = float(self.VNom2LineEdit.text())
                trafo[0].jx0 = float(self.XZeroSeqTrafoLineEdit.text())
                trafo[0].jx1 = float(self.XPosSeqTrafoLineEdit.text())
                trafo[0].connection = self.TrafoConnection.currentText()
                self.LayoutManager()
        except Exception:
            logging.error(traceback.format_exc())


    def addNewLineType(self):
        try:
            global LINE_TYPES
            layout = self.InputNewLineTypeFormLayout
            new_values = list(layout.itemAt(i).widget().text() for i in range(layout.count()) \
                              if not isinstance(layout.itemAt(i), QLayout))
            titles = new_values[:2]
            par_names = new_values[2::2]
            par_values = new_values[3::2]
            print(titles, par_names, par_values)
            if any(map(lambda x: x[0] == titles[1], LINE_TYPES)):
                self._statusMsg.emit_sig('Duplicated name. Insert another valid name')
                return
            elif any(map(lambda x: x == '', par_values)):
                self._statusMsg.emit_sig('Undefined parameter. Fill all parameters')
                return
            elif any(map(lambda x: par_values == list(x[1].values()), LINE_TYPES)):
                self._statusMsg.emit_sig('A similar model was identified. The model has been not stored')
                return
            else:
                LINE_TYPES.append([titles[1], {par_names[i]: float(par_values[i]) for i in range(len(par_names))}])
                self._statusMsg.emit_sig('The model has been stored')
        except Exception:
            logging.error(traceback.format_exc())
        finally:
            print(LINE_TYPES)


    def hideSpacer(self):
        self.Spacer.changeSize(0, 0)


    def showSpacer(self):
        self.Spacer.changeSize(200, 0)


    def setLayoutHidden(self, layout, visible):
        """Hide recursivelly any layout containing widgets or/and other layouts
        """
        witems = list(layout.itemAt(i).widget() for i in range(layout.count()) \
                      if not isinstance(layout.itemAt(i), QLayout))
        witems = list(filter(lambda x: x is not None, witems))
        for w in witems: w.setHidden(visible)
        litems = list(layout.itemAt(i).layout() for i in range(layout.count()) if isinstance(layout.itemAt(i), QLayout))
        for children_layout in litems: self.setLayoutHidden(children_layout, visible)


    def settemp(self, args):
        """This method stores the first line in line element drawing when inputting lines.
        Its existence is justified by the first square limitation in MouseMoveEvent
        """
        self._temp = args


    def storeOriginAddLt(self):
        if self._startNewLT:
            self._ltorigin = self._currElementCoords


    def add_line(self):
        # args = [(i, j), line]
        # TL = [[TL, lines, coordinates, bool ToExclude, ]
        global TL
        try:
            if self._startNewLT:
                print('Colocando nova linha\n')
                NEW_TL = LT(origin=self._ltorigin)
                if not self.checkTlCrossing():
                    TL.append([NEW_TL, [], [], False])
                else:
                    print('Linha cruzou na saída\n')
                    TL.append([NEW_TL, [], [], True])
                TL[-1][1].append(self._temp)
                TL[-1][2].append(self._ltorigin)
                TL[-1][2].append(self._currElementCoords)
            else:
                print('Continuando linha\n')
                if self.checkTlCrossing():
                    TL[-1][3] = True
                    print('Linha cruzou com alguma outra já existente\n')
                TL[-1][1].append(self._temp)
                TL[-1][2].append(self._currElementCoords)
                if isinstance(GRID_BUSES[self._currElementCoords], Barra):
                    if TL[-1][0].destiny is None:
                        TL[-1][0].destiny = self._currElementCoords
            self._startNewLT = False
        except Exception:
            logging.error(traceback.format_exc())


    def checkTlCrossing(self):
        global TL
        for tl in TL:
            if self._currElementCoords in tl[2] and not isinstance(GRID_BUSES[self._currElementCoords], Barra):
                return True
            else:
                continue
        return False


    def remove_selected_trafo(self, trafo=None):
        """Remove an trafo. If parameters trafo is not passed, the method will find it from the selection in GRID.
        Else, the passed trafo will be deleted
        """
        global TRANSFORMERS
        if trafo is None:
            if self.getTrafoFromGridPos(self._currElementCoords) is not None:
                trafo = self.getTrafoFromGridPos(self._currElementCoords)
            else:
                pass
        for linedrawing in trafo[1]:
            self.Scene.removeItem(linedrawing)
        TRANSFORMERS.remove(trafo)
        print('len(TRANSFORMERS) = ', len(TRANSFORMERS))


    def remove_selected_line(self, line=None):
        global TL
        if line is None:
            if self.getLtFromGridPos(self._currElementCoords):
                line = self.getLtFromGridPos(self._currElementCoords)
            else:
                pass
        for linedrawing in line[1]:
            self.Scene.removeItem(linedrawing)
        TL.remove(line)
        print('len(TL) = ', len(TL))


    def remove_pointless_lines(self):
        """If line's bool remove is True, the line will be removed.
        The remove may have three causes:
        1. The line crossed with itself or with another line
        2. The line was inputted with only two points
        3. The line has not a destiny bar
        """
        global TL
        try:
            for line in TL:
                if line[3]:
                    for linedrawing in line[1]:
                        self.Scene.removeItem(linedrawing)
                    TL.remove(line)
        except Exception:
            logging.error(traceback.format_exc())


    def isLastLineDuplicated(self):
        """This method is being used only for lines with two points
        """
        try:
            last_line = TL[-1]
            assert len(last_line[2]) == 2
            filtered = TL.copy()
            filtered.remove(last_line)
            filtered = list(filter(lambda x: len(x[2]) == 2, filtered))
            print('isLastLineDuplicated >>> filtered: \n', filtered)
            if len(filtered) > 1:
                for other_line in filtered:
                    if last_line[2] == other_line[2]:
                        return True
                    else:
                        continue
                return False
        except Exception:
            logging.error(traceback.format_exc())



    def doAfterMouseRelease(self):
        global TL
        self._startNewLT = True
        try:
            if TL:
                if len(TL[-1][2]) == 2:  # If the line has two points only
                    TL[-1][3] = True # Remove
                else:  # If the line has more than two points
                    if TL[-1][0].destiny is None:  # If line has not destiny bus
                        TL[-1][3] = True  # Remove line
            self.remove_pointless_lines()  # Removes all lines with bool remove = True
            for lt in TL:
                assert(lt[0].origin is not None)
                assert(lt[0].destiny is not None)
            self.LayoutManager()
        except Exception:
            logging.error(traceback.format_exc())


    def methodsTrigger(self, args):
        self.__calls[args]()


    def setCurrentObject(self, args):
        self._currElementCoords = args


    def updateBusInspector(self, BUS=0):
        """Updates the BI with bus data if bus existes or
        show that there's no bus (only after bus exclusion)
        ---------------------------------------------------
        Called by: LayoutManager, remove_gen
        ---------------------------------------------------
        """
        if BUS:
            if BUS.barra_id == 0:
                self.BarTitle.setText('Barra Slack'.format(BUS.barra_id))
            else:
                self.BarTitle.setText('Barra {}'.format(BUS.barra_id))
            self.BarV_Value.setText('{:.1f}'.format(np.abs(BUS.v)))
            self.BarAngle_Value.setText('{:.1f}º'.format(np.angle(BUS.v)))
            self.QgInput.setText('{:.1f}'.format(BUS.qg))
            self.PgInput.setText('{:.1f}'.format(BUS.pg))
            self.QlInput.setText('{:.1f}'.format(BUS.ql))
            self.PlInput.setText('{:.1f}'.format(BUS.pl))
        else:
            self.BarTitle.setText('No bar')
            self.BarV_Value.setText('{:.1f}'.format(0.0))
            self.BarAngle_Value.setText('{:.1f}º'.format(0.0))
            self.QgInput.setText('{:.1f}'.format(0.0))
            self.PgInput.setText('{:.1f}'.format(0.0))
            self.QlInput.setText('{:.1f}'.format(0.0))
            self.PlInput.setText('{:.1f}'.format(0.0))


    def LayoutManager(self):
        """Hide or show specific layouts, based on the current element or passed parameters by trigger methods.
        Called two times ever because self.doAfterMouseRelease is triggered whenever the mouse is released
        ------------------------------------------------------------------------------------------------------
        Called by: self.doAfterMouseRelease (after input), add_bus, remove_bus, self.removeLTPushButton,
                   self.removeTrafoPushButton, self.lineProcessing, self.trafoProcessing
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
                self.updateTrafoInspector()
            else:
                # No element case
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, True)
                self.setLayoutHidden(self.InputNewLineType, True)
                self.showSpacer()
        except Exception:
            print(logging.error(traceback.format_exc()))


    def add_bus(self):
        try:
            global GRID_BUSES, ID, BUSES
            COORDS = self._currElementCoords
            if not isinstance(GRID_BUSES[COORDS], Barra):
                if all([BUS.barra_id > 0 for BUS in BUSES]) or np.size(BUSES) == 0:
                    # first add, or add after bus' exclusion
                    SLACK = Barra(barra_id=0, posicao=COORDS)
                    BUSES.insert(0, SLACK)
                    GRID_BUSES[COORDS] = SLACK
                elif any([BUS.barra_id == 0 for BUS in BUSES]) and np.size(BUSES) > 0:
                    # sequenced bus insert
                    BUS = Barra(barra_id=ID, posicao=COORDS)
                    GRID_BUSES[COORDS] = BUS
                    BUSES.append(BUS)
                    ID += 1
                self.LayoutManager()
            else:
                self._statusMsg.emit_sig('There\'s a bus in this position!')
        except Exception:
            logging.error(traceback.format_exc())


    def remove_bus(self):
        global ID, BUSES, GRID_BUSES, BUSES_PIXMAP
        try:
            if GRID_BUSES[self._currElementCoords]:
                BUS = self.getBusFromGridPos(self._currElementCoords)
                self.removeElementsLinked2Bus(BUS)
                if BUS.barra_id != 0:
                    ID -= 1
                    BUSES.remove(BUS)
                    for i in range(1, ID):
                        BUSES[i].barra_id = i
                elif BUS.barra_id == 0:
                    BUSES.remove(BUS)
                self.Scene.removeItem(BUSES_PIXMAP[self._currElementCoords])
                BUSES_PIXMAP[self._currElementCoords] = 0
                GRID_BUSES[self._currElementCoords] = 0
                self.updateBusInspector(self.getBusFromGridPos(self._currElementCoords))
                self.LayoutManager()
        except Exception:
            logging.error(traceback.format_exc())


    @staticmethod
    def getBusFromGridPos(COORDS):
        """Returns the position in BUSES array and the BUS itself, given an bus from GRID_ELEMENT"""
        grid_bus = GRID_BUSES[COORDS]
        if isinstance(grid_bus, Barra):
            for bus in BUSES:
                if bus.posicao == grid_bus.posicao:
                    return bus
                else:
                    continue
        return None


    @staticmethod
    def getLtFromGridPos(COORDS):
        """Returns the TL's position (in TL) and TL element, given the grid coordinates"""
        for tl in TL:
            if COORDS in tl[2]:
                return tl
            else:
                continue
        return None


    @staticmethod
    def getTrafoFromGridPos(COORDS):
        """Returns the TRAFO'S position (in TRAFOS) and TRAFO element, given the grid coordinates"""
        for trafo in TRANSFORMERS:
            if COORDS in trafo[2]:
                return trafo
            else:
                continue
        return None


    def removeElementsLinked2Bus(self, BUS):
        global TL, TRANSFORMERS
        linked_lts, linked_trfs = [], []
        for line in TL:
            if BUS.posicao in line[2]:
                linked_lts.append(line)
        for removing_lts in linked_lts: self.remove_selected_line(removing_lts)
        for trafo in TRANSFORMERS:
            if BUS.posicao in trafo[2]:
                linked_trfs.append(trafo)
        for removing_trfs in linked_trfs: self.remove_selected_trafo(removing_trfs)


    def add_gen(self):
        """
        Adds generation to the bus, desblocks some QLineEdits
        -----------------------------------------------------
        Called by: QPushButton Add generation (__init__)
        -----------------------------------------------------------
        Consideering: any generation is non-grounded star connected
        -----------------------------------------------------------
        """
        try:
            global BUSES
            # TODO problema no 'abandono' das entradas da geração
            BUS = self.getBusFromGridPos(self._currElementCoords)
            self.BarV_Value.setEnabled(True)
            if BUS.barra_id != 0:
                self.PgInput.setEnabled(True)
                self.XdLineEdit.setEnabled(True)
            self.AddGenerationButton.setText('OK')
            self._statusMsg.emit_sig('Input generation data...')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.submit_gen)
        except Exception:
            logging.error(traceback.format_exc())


    def submit_gen(self):
        """Updates bus parameters with the user input in BI
        ---------------------------------------------------
        Called by: add_gen (button rebind)
        ----------------------------------
        """
        global GRID_BUSES, BUSES
        if isinstance(GRID_BUSES[self._currElementCoords], Barra):
            BUS = self.getBusFromGridPos(self._currElementCoords)
            BUS.v = float(self.BarV_Value.text())
            BUS.pg = float(self.PgInput.text())
            BUS.xd = float(self.XdLineEdit.text())
            GRID_BUSES[self._currElementCoords].v = BUS.v
            GRID_BUSES[self._currElementCoords].pg = BUS.pg
            GRID_BUSES[self._currElementCoords].xd = BUS.xd
            self._statusMsg.emit_sig('Added generation')
            print('Barra atualizada')
            print('V da barra: {0}, Pg da barra: {1}'.format(BUS.v, BUS.pg))
            self.BarV_Value.setEnabled(False)
            self.PgInput.setEnabled(False)
            self.XdLineEdit.setEnabled(False)
            self.AddGenerationButton.setText('-')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.remove_gen)


    def remove_gen(self):
        global GRID_BUSES, BUSES
        if isinstance(GRID_BUSES[self._currElementCoords], Barra):
            BUS = self.getBusFromGridPos(self._currElementCoords)
            BUS.v = 0
            BUS.pg = 0
            BUS.xd = 0
            GRID_BUSES[self._currElementCoords].v = 0
            GRID_BUSES[self._currElementCoords].pg = 0
            GRID_BUSES[self._currElementCoords].xd = 0
            self._statusMsg.emit_sig('Removed generation')
            print('Geração removida')
            print('V da barra: {0}, Pg da barra: {1}'.format(BUS.v, BUS.pg))
            self.updateBusInspector(BUS)
            self.AddGenerationButton.setText('+')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.add_gen)


    def add_load(self):
        """
        ------------------------------------------
        Called by: QPushButton Add load (__init__)
        ------------------------------------------
        Consideering: any load is grounded in star connection
        """
        try:
            global BUSES
            self.PlInput.setEnabled(True)
            self.QlInput.setEnabled(True)
            self.AddLoadButton.setText('OK')
            self._statusMsg.emit_sig('Input load data...')
            self.AddLoadButton.disconnect()
            self.AddLoadButton.pressed.connect(self.submit_load)
        except Exception:
            logging.error(traceback.format_exc())


    def submit_load(self):
        """Updates bus parameters with the user input in BI
        ---------------------------------------------------
        Called by: add_load (button rebind)
        ----------------------------------
        """
        global GRID_BUSES, BUSES
        try:
            if isinstance(GRID_BUSES[self._currElementCoords], Barra):
                BUS = self.getBusFromGridPos(self._currElementCoords)
                BUS.pl = float(self.PlInput.text())
                BUS.ql = float(self.QlInput.text())
                GRID_BUSES[self._currElementCoords].pl = BUS.pl
                GRID_BUSES[self._currElementCoords].ql = BUS.ql
                self._statusMsg.emit_sig('Added load')
                print('Barra atualizada')
                print('Pl da barra: {0}, Ql da barra: {1}'.format(BUS.pl, BUS.ql))
                self.PlInput.setEnabled(False)
                self.QlInput.setEnabled(False)
                self.AddLoadButton.setText('-')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.remove_load)
        except Exception:
            logging.error(traceback.format_exc())


    def remove_load(self):
        try:
            global GRID_BUSES, BUSES
            if isinstance(GRID_BUSES[self._currElementCoords], Barra):
                BUS = self.getBusFromGridPos(self._currElementCoords)
                BUS.pl = 0
                BUS.ql = 0
                GRID_BUSES[self._currElementCoords].pl = 0
                GRID_BUSES[self._currElementCoords].ql = 0
                self._statusMsg.emit_sig('Removed load')
                print('Carga removida')
                print('Pl da barra: {0}, Ql da barra: {1}'.format(BUS.pl, BUS.ql))
                self.updateBusInspector(BUS)
                self.AddLoadButton.setText('+')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.add_load)
        except Exception:
            logging.error(traceback.format_exc())


class Aspy(QMainWindow):
    def __init__(self):
        super(Aspy, self).__init__()
        self.initUI()

    def initUI(self):
        self.statusBar().showMessage('Ready')

        ### Actions ###
        saveAct = QAction('Save current session', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.saveSession)

        loadAct = QAction('Load current session', self)
        loadAct.setShortcut('Ctrl+O')
        loadAct.triggered.connect(self.loadSession)

        addLineAct = QAction('Add line type', self)
        addLineAct.triggered.connect(self.addLineType)

        editLineAct = QAction('Edit line type', self)
        editLineAct.triggered.connect(self.editLineType)

        setDefaultLineAct = QAction('Set default line type', self)
        setDefaultLineAct.triggered.connect(self.setDefaultLineType)

        ### ======== Central widget =========== ###
        self.CircuitInputer = CircuitInputer()
        self.CircuitInputer._statusMsg.signal.connect(lambda args: self.displayStatusMsg(args))
        self.setCentralWidget(self.CircuitInputer)

        ### Menu bar ###
        menubar = self.menuBar()

        filemenu = menubar.addMenu('&Session')
        filemenu.addAction(saveAct)
        filemenu.addAction(loadAct)

        linemenu = menubar.addMenu('&Lines')
        linemenu.addAction(addLineAct)
        linemenu.addAction(editLineAct)

        settings = menubar.addMenu('&Settings')
        settings.addAction(setDefaultLineAct)


        self.setWindowTitle('Aspy')
        self.setGeometry(50, 50, 1000, 600)
        self.setMinimumWidth(1000)
        self.show()

    def setDefaultLineType(self):
        pass

    def displayStatusMsg(self, args):
        self.statusBar().showMessage(args)

    def saveSession(self):
        pass

    def loadSession(self):
        pass

    def addLineType(self):
        print('add line type')
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.InputNewLineType, False)
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.BarLayout, True)
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.LtOrTrafoLayout, True)


    def editLineType(self):
        print('edit line type')


def getSessionsDir():
    if sys.platform in ('win32', 'win64'):
        home_dir = os.getenv('userprofile')
        sessions_dir = os.path.join(home_dir, 'Documents\\aspy')
    return sessions_dir


if __name__ == '__main__':
    app = QApplication(sys.argv)
    aspy = Aspy()
    sys.exit(app.exec_())