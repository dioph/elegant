import logging
import sys
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import QPen, QPixmap, QBrush
from PyQt5.QtWidgets import *

from aspy.core import *

N = 20  # grid size in schemeinputer
ID = 1  # 0 for slack bus
GRID_ELEMENTS = np.zeros((N, N), object)  # hold the aspy.core elements
BUSES_PIXMAP = np.zeros((N, N), object)  # hold the buses drawings
BUSES = np.zeros((0,), object)  # hold the buses
TL = []  # hold the transmission lines
# TL = [[TL, coordinates], ]
LINE_TYPES = []  # hold the types of transmission lines
TRANSFORMERS = []  # hold the transformers


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
        line = self.addLine(coordinates[0, 0], coordinates[0, 1], coordinates[1, 0], coordinates[1, 1], pen)
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
        # TODO: bug in clearing square after scrolling in any direction
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
                    pixmap = QPixmap('./data/buttons/DOT.jpg')
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
                        self._methodSignal.emit_sig('showInspector')
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
                            if isinstance(GRID_ELEMENTS[i, j], Barra):  # Asserts the start was from a bus
                                self._firstRetainer = False
                        if central_point.x() != self._moveHistory[0, 0] \
                                or central_point.y() != self._moveHistory[0, 1]:  # Set destiny
                            self._moveHistory[1, 0] = central_point.x(); self._moveHistory[1, 1] = central_point.y()
                        if (np.all(self._moveHistory > 0)) and \
                                (np.any(self._moveHistory[0, :] != np.any(self._moveHistory[1, :]))):
                            ### DRAW LINE ###
                            try:
                                if isinstance(GRID_ELEMENTS[i, j], Barra) and not self._firstRetainer:
                                    # when a bus is achieved
                                    line = self.drawLine(self._moveHistory)
                                    self._moveHistory[:, :] = -1
                                    self._lastRetainer = True  # Prevent the user for put line outside last bus
                                    self._pointerSignal.emit_sig((i, j))
                                    self._dataSignal.emit_sig(line)
                                    self._methodSignal.emit_sig('addLine')
                                elif not isinstance(GRID_ELEMENTS[i, j], Barra) and not (self._lastRetainer or self._firstRetainer):
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
        self._currentElement = None  # coordinates to current object being manipuled
        self._startNewLine = True
        self._ltorigin = None
        self._temp = None
        self._statusMsg = GenericSignal()
        self.__calls = {'addBus': self.add_bus,
                        'addLine': self.add_line,
                        'showInspector': self.showInspector,
                        'mouseReleased': self.startNewLine,
                        'storeOriginAddLt': self.storeOriginAddLt}
        self.Scene._pointerSignal.signal.connect(lambda args: self.setCurrentObject(args))
        self.Scene._dataSignal.signal.connect(lambda args: self.settemp(args))
        self.Scene._methodSignal.signal.connect(lambda args: self.methodsTrigger(args))

        ### ========================= Inspectors =================================== ###
        self.InspectorLayout = QVBoxLayout()
        self.TypeLayout = QHBoxLayout()
        self.TypeLayout.addStretch()
        self.InspectorLayout.addLayout(self.TypeLayout)
        self.TypeLayout.addStretch()

        ## Layout for general bar case ###
        self.BarLayout = QVBoxLayout()

        ### Bus title ###
        self.BarTitle = QLabel('Bar title')
        self.BarTitle.setAlignment(Qt.AlignCenter)

        ### Bus voltage ###
        self.BarV_Value = QLineEdit('0.0')
        self.BarV_Value.setEnabled(False)

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

        ### Line edit to input bus Pg ###
        self.PgInput = QLineEdit('0.0')
        self.PgInput.setEnabled(False)

        ### Line edit to input bus Qg ###
        self.QgInput = QLineEdit('0.0')
        self.QgInput.setEnabled(False)

        ### Adding Pg, Qg to add generation FormLayout ###
        self.AddGenerationFormLayout.addRow('Qg', self.QgInput)
        self.AddGenerationFormLayout.addRow('Pg', self.PgInput)

        ### Label with 'Carga' ###
        self.AddLoadLabel = QLabel('Carga')
        self.AddLoadLabel.setAlignment(Qt.AlignCenter)

        ### PushButton that binds to three different methods ###
        self.AddLoadButton = QPushButton('+')
        self.AddLoadButton.pressed.connect(self.add_load)

        ### LineEdit with Ql, Pl ###
        self.QlInput = QLineEdit('0.0')
        self.PlInput = QLineEdit('0.0')
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
        self.BarLayout.addWidget(self.AddLoadLabel)
        self.BarLayout.addWidget(self.AddLoadButton)
        self.BarLayout.addWidget(self.RemoveBus)

        ### Layout for input new type of line ###
        self.InputNewLineType = QVBoxLayout()
        self.InputNewLineTypeFormLayout = QFormLayout()

        self.chooseParameters = QRadioButton('Parameters')
        self.chooseParameters.toggled.connect(self.chooseNewLineTypeInputManner)
        self.chooseImpedance = QRadioButton('Impedance')
        self.chooseImpedance.toggled.connect(self.chooseNewLineTypeInputManner)
        self.chooseLayout = QHBoxLayout()
        self.chooseLayout.addWidget(self.chooseParameters)
        self.chooseLayout.addWidget(self.chooseImpedance)

        self.ModelName = QLineEdit()
        self.YLineEdit = QLineEdit()
        self.ZLineEdit = QLineEdit()

        self.RhoLineEdit = QLineEdit()
        self.EllLineEdit = QLineEdit()
        self.rLineEdit = QLineEdit()
        self.d12LineEdit = QLineEdit()
        self.d23LineEdit = QLineEdit()
        self.d31LineEdit = QLineEdit()
        self.dLineEdit = QLineEdit()
        self.mLineEdit = QLineEdit()

        self.InputNewLineTypeFormLayout.addRow('Name', self.ModelName)
        self.InputNewLineTypeFormLayout.addRow('Y', self.YLineEdit)
        self.InputNewLineTypeFormLayout.addRow('Z', self.ZLineEdit)
        self.InputNewLineTypeFormLayout.addRow('\u03c1', self.RhoLineEdit)
        self.InputNewLineTypeFormLayout.addRow('\u2113', self.EllLineEdit)
        self.InputNewLineTypeFormLayout.addRow('r', self.rLineEdit)
        self.InputNewLineTypeFormLayout.addRow('d12', self.d12LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d23', self.d23LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d31', self.d31LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d', self.dLineEdit)
        self.InputNewLineTypeFormLayout.addRow('m', self.mLineEdit)

        self.InputNewLineType.addStretch()
        self.InputNewLineType.addLayout(self.chooseLayout)
        self.InputNewLineType.addLayout(self.InputNewLineTypeFormLayout)
        self.SubmitNewLineTypePushButton = QPushButton('Submit')
        self.SubmitNewLineTypePushButton.pressed.connect(self.addNewLineType)
        self.InputNewLineType.addWidget(self.SubmitNewLineTypePushButton)
        self.InputNewLineType.addStretch()

        ### General Layout for LT case ###
        self.LtOrTrafoLayout = QVBoxLayout()

        self.chooseLt = QRadioButton('LT')
        self.chooseLt.toggled.connect(self.defineLtOrTrafoVisibility)
        self.chooseTrafo = QRadioButton('Trafo')
        self.chooseLtOrTrafo = QHBoxLayout()
        self.chooseLtOrTrafo.addWidget(QLabel('LT/Trafo:'))
        self.chooseLtOrTrafo.addWidget(self.chooseLt)
        self.chooseLtOrTrafo.addWidget(self.chooseTrafo)

        self.chooseLtFormLayout = QFormLayout()
        self.chooseLtModel = QComboBox()
        self.chooseLtModel.currentIndexChanged.connect(self.updateLtParameters)
        self.removeLTPushButton = QPushButton('Remove LT')
        self.removeLTPushButton.pressed.connect(self.remove_line)
        self.chooseLtFormLayout.addRow('Model   ', self.chooseLtModel)
        self.chooseLtFormLayout.addRow('', self.removeLTPushButton)

        self.chooseTrafoFormLayout = QFormLayout()
        self.XTrafoLineEdit = QLineEdit()
        self.VNom1LineEdit = QLineEdit()
        self.VNom2LineEdit = QLineEdit()
        self.chooseTrafoSubmitButton = QPushButton('Submit')
        self.chooseTrafoFormLayout.addRow('X', self.XTrafoLineEdit)
        self.chooseTrafoFormLayout.addRow('VNom 1', self.VNom1LineEdit)
        self.chooseTrafoFormLayout.addRow('VNom 2', self.VNom2LineEdit)
        self.chooseTrafoFormLayout.addRow('', self.chooseTrafoSubmitButton)

        self.LtOrTrafoLayout.addLayout(self.chooseLtOrTrafo)
        self.LtOrTrafoLayout.addLayout(self.chooseLtFormLayout)
        self.LtOrTrafoLayout.addLayout(self.chooseTrafoFormLayout)

        ### Layout that holds bus inspector and Stretches ###
        self.InspectorAreaLayout = QVBoxLayout()
        self.InspectorLayout.addLayout(self.BarLayout)
        self.InspectorLayout.addLayout(self.LtOrTrafoLayout)
        self.InspectorAreaLayout.addLayout(self.InspectorLayout)

        ### All layouts hidden at first moment ###
        self.setLayoutHidden(self.BarLayout, True)
        self.setLayoutHidden(self.InputNewLineType, True)
        self.setLayoutHidden(self.LtOrTrafoLayout, True)
        self.setLayoutHidden(self.chooseTrafoFormLayout, True)

        ### Toplayout ###
        self.TopLayout = QHBoxLayout()
        self.TopLayout.addLayout(self.InspectorAreaLayout)
        self.TopLayout.addLayout(self.SchemeInputLayout)
        self.TopLayout.addLayout(self.InputNewLineType)
        self.setLayout(self.TopLayout)


    def defineLtOrTrafoVisibility(self):
        if self.chooseLt.isChecked():
            self.setLayoutHidden(self.chooseLtFormLayout, False)
            self.setLayoutHidden(self.chooseTrafoFormLayout, True)
        else:
            self.setLayoutHidden(self.chooseLtFormLayout, True)
            self.setLayoutHidden(self.chooseTrafoFormLayout, False)


    def updateLToptions(self):
        for model in LINE_TYPES:
            if self.chooseLtModel.findText(model[0]) == -1:
                self.chooseLtModel.addItem(model[0])
            else:
                pass


    def updateLtParameters(self):
        print(self.chooseLtModel.currentText())
        POS, ELEMENT = self.getLtPosFromGridPos(self._currentElement)


    def chooseNewLineTypeInputManner(self):
        layout = self.InputNewLineTypeFormLayout
        linedits = list(layout.itemAt(i).widget() for i in range(layout.count()) \
                        if isinstance(layout.itemAt(i).widget(), QLineEdit))
        if self.chooseImpedance.isChecked():
            for linedit in linedits[3:]:
                linedit.setEnabled(False)
                linedit.setText('')
            for linedit in linedits[1:3]:
                linedit.setEnabled(True)
        else:
            for linedit in linedits[3:]:
                linedit.setEnabled(True)
            for linedit in linedits[1:3]:
                linedit.setEnabled(False)
                linedit.setText('')
        print(LINE_TYPES)


    def addNewLineType(self):
        global LINE_TYPES
        layout = self.InputNewLineTypeFormLayout
        new_values = list(layout.itemAt(i).widget().text() for i in range(layout.count()) \
                          if not isinstance(layout.itemAt(i), QLayout))
        name = new_values[1] if new_values[1] != '' else 'model {}'.format(len(LINE_TYPES)+1)
        name_values_par = new_values[6::2]; name_values_imp = new_values[2:6:2]
        number_values_imp = new_values[3:7:2]; number_values_par = new_values[7::2]
        try:
            if all(map(lambda x: x[0] != name, LINE_TYPES)):
                if all(map(lambda x: x != '', number_values_imp)):
                    if np.size(LINE_TYPES) == 0:
                        LINE_TYPES.append([name, {name_values_imp[i]: float(number_values_imp[i]) \
                                                       for i in range(len(number_values_imp))}])
                        self._statusMsg.emit_sig('Model recorded')
                    else:
                        filtered = list(filter(lambda array: len(list(array[1].values())) == 2, LINE_TYPES))
                        if all(list(map(lambda x: float(x), number_values_imp)) != list(type[1].values()) for type in filtered):
                            LINE_TYPES.append([name, {name_values_imp[i]: float(number_values_imp[i]) \
                                                      for i in range(len(number_values_imp))}])
                            self._statusMsg.emit_sig('Model recorded')
                        else:
                            self._statusMsg.emit_sig('This model has been already stored')
                elif all(map(lambda x: x != '', number_values_par)):
                    if len(LINE_TYPES) == 0:
                        LINE_TYPES.append([name, {name_values_par[i]: float(number_values_par[i]) \
                                                  for i in range(len(number_values_par))}])
                        self._statusMsg.emit_sig('Model recorded')
                    else:
                        filtered = list(filter(lambda array: len(list(array[1].values())) == 8, LINE_TYPES))
                        if all(list(map(lambda x: float(x), number_values_par)) != list(type[1].values()) for type in filtered):
                            LINE_TYPES.append([name, {name_values_par[i]: float(number_values_par[i]) \
                                                      for i in range(len(number_values_par))}])
                            self._statusMsg.emit_sig('Model recorded')
                        else:
                            self._statusMsg.emit_sig('This model has been already stored')
                self.setLayoutHidden(self.InputNewLineType, True)
                self.updateLToptions()
                self.updateLtParameters()
                print(LINE_TYPES)
            else:
                self._statusMsg.emit_sig('The specified name already exists. Input another name for model')
        except TypeError:
            self._statusMsg.emit_sig('Invalid input catched: you must input only float numbers')
        except Exception:
            logging.error(traceback.format_exc())


    def setLayoutHidden(self, layout, visible):
        witems = list(layout.itemAt(i).widget() for i in range(layout.count()) \
                      if not isinstance(layout.itemAt(i), QLayout))
        witems = list(filter(lambda x: x is not None, witems))
        for w in witems: w.setHidden(visible)
        litems = list(layout.itemAt(i).layout() for i in range(layout.count()) if isinstance(layout.itemAt(i), QLayout))
        for layout in litems: self.setLayoutHidden(layout, visible)


    def settemp(self, args):
        self._temp = args
        print(self._temp)


    def storeOriginAddLt(self):
        if self._startNewLine:
            self._ltorigin = self._currentElement


    def add_line(self):
        global TL
        # args = [(i, j), line]
        # TL = [[TL, line, coordinates], ]
        try:
            if self._startNewLine:
                NEW_TL = LT(origin=self._ltorigin)
                TL.append([NEW_TL, [], []])
                TL[-1][1].append(self._temp)
                TL[-1][2].append(self._ltorigin)
                TL[-1][2].append(self._currentElement)
            else:
                TL[-1][1].append(self._temp)
                TL[-1][2].append(self._currentElement)
                if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                    if TL[-1][0].destiny is None:
                        TL[-1][0].destiny = self._currentElement
            self._startNewLine = False
        except Exception:
            logging.error(traceback.format_exc())


    def remove_line(self):
        try:
            RemovingTlPosition, RemovingTl = self.getLtPosFromGridPos(self._currentElement)
            print(RemovingTlPosition)
            for line in RemovingTl[1]:
                self.Scene.removeItem(line)
            TL.remove(RemovingTl)
        except Exception:
            logging.error(traceback.format_exc())


    def startNewLine(self):
        self._startNewLine = True


    def methodsTrigger(self, args):
        self.__calls[args]()


    def setCurrentObject(self, args):
        self._currentElement = args


    def updateBusInspector(self, BUS=0):
        if BUS:
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


    def showInspector(self):
        ELEMENT = GRID_ELEMENTS[self._currentElement]
        try:
            if isinstance(ELEMENT, Barra):
                self.chooseLt.setChecked(False)
                self.chooseTrafo.setChecked(False)
                self.setLayoutHidden(self.BarLayout, False)
                self.setLayoutHidden(self.LtOrTrafoLayout, True)
                self.updateBusInspector(ELEMENT)
            else:
                try:
                    POS, ELEMENT = self.getLtPosFromGridPos(self._currentElement)
                except TypeError:
                    pass
                else:
                    self.chooseLt.setChecked(False)
                    self.chooseTrafo.setChecked(False)
                    self.setLayoutHidden(self.BarLayout, True)
                    self.setLayoutHidden(self.LtOrTrafoLayout, False)
                    self.setLayoutHidden(self.chooseLtFormLayout, True)
                    self.setLayoutHidden(self.chooseTrafoFormLayout, True)
        except Exception:
            print(logging.error(traceback.format_exc()))


    def add_bus(self):
        global GRID_ELEMENTS, ID, BUSES
        COORDS = self._currentElement
        if all([BUS.barra_id > 0 for BUS in BUSES]) or np.size(BUSES) == 0:
            # first add, or add after bus' exclusion
            SLACK = Barra(barra_id=0, posicao=COORDS)
            BUSES = np.insert(BUSES, 0, SLACK)
            GRID_ELEMENTS[COORDS] = SLACK
        elif any([BUS.barra_id == 0 for BUS in BUSES]) and np.size(BUSES) > 0:
            # sequenced bus insert
            BUS = Barra(barra_id=ID, posicao=COORDS)
            GRID_ELEMENTS[COORDS] = BUS
            BUSES = np.append(BUSES, BUS)
            ID += 1
        self.showInspector()


    def remove_bus(self):
        global ID, BUSES, GRID_ELEMENTS, BUSES_PIXMAP
        if GRID_ELEMENTS[self._currentElement]:
            POS, BUS = self.getBusFromGridEl(GRID_ELEMENTS[self._currentElement])
            if BUS.barra_id != 0:
                ID -= 1
                BUSES = np.delete(BUSES, POS)
                for i in range(1, ID):
                    BUSES[i].barra_id = i
            elif BUS.barra_id == 0:
                BUSES = np.delete(BUSES, POS)
            self.Scene.removeItem(BUSES_PIXMAP[self._currentElement])
            BUSES_PIXMAP[self._currentElement] = 0
            GRID_ELEMENTS[self._currentElement] = 0
            self.updateBusInspector(GRID_ELEMENTS[self._currentElement])
            self.showInspector()


    def add_gen(self):
        print('add_gen')
        self.BarV_Value.setEnabled(True)
        self.PgInput.setEnabled(True)
        self.AddGenerationButton.setText('OK')
        self.AddGenerationButton.disconnect()
        self.AddGenerationButton.pressed.connect(self.submit_gen)


    @staticmethod
    def getBusFromGridEl(GRID_ELEMENT):
        """Returns the position in BUSES array and the BUS itself, given an element from GRID_ELEMENT"""
        for POS, BUS in enumerate(BUSES):
            if BUS.posicao == GRID_ELEMENT.posicao:
                return POS, BUS


    @staticmethod
    def getLtPosFromGridPos(COORDS):
        """Returns the TL's position (in TL) and TL element, given the grid coordinates"""
        for pos, tl in enumerate(TL):
            if COORDS in tl[2]:
                return pos, tl


    def submit_gen(self):
        global GRID_ELEMENTS, BUSES
        print('submit_gen')
        if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
            GRID_ELEMENTS[self._currentElement].v = complex(self.BarV_Value.text())
            GRID_ELEMENTS[self._currentElement].pg = float(self.PgInput.text())
            POS, _ = self.getBusFromGridEl(GRID_ELEMENTS[self._currentElement])
            BUSES[POS].v = complex(self.BarV_Value.text())
            BUSES[POS].pg = float(self.PgInput.text())
            self.AddGenerationButton.setText('-')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.remove_gen)


    def remove_gen(self):
        global GRID_ELEMENTS, BUSES
        print('remove_gen')
        if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
            GRID_ELEMENTS[self._currentElement].v = complex(0)
            GRID_ELEMENTS[self._currentElement].pg = 0.0
            POS, _ = self.getBusFromGridEl(GRID_ELEMENTS[self._currentElement])
            BUSES[POS].v = complex(0)
            BUSES[POS].pg = 0.0
            self.BarV_Value.setEnabled(False)
            self.PgInput.setEnabled(False)
            self.BarV_Value.setText(str(GRID_ELEMENTS[self._currentElement].v))
            self.PgInput.setText(str(GRID_ELEMENTS[self._currentElement].pg))
            self.AddGenerationButton.setText('+')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.add_gen)


    def add_load(self):
        print('add_load')
        self.PlInput.setEnabled(True)
        self.QlInput.setEnabled(True)
        self.AddLoadButton.setText('OK')
        self.AddLoadButton.disconnect()
        self.AddLoadButton.pressed.connect(self.submit_load)


    def submit_load(self):
        print('submit_load')
        self.AddLoadButton.setText('-')
        self.AddLoadButton.disconnect()
        self.AddLoadButton.pressed.connect(self.remove_load)


    def remove_load(self):
        print('remove_load')
        self.AddLoadButton.setText('+')
        self.AddLoadButton.disconnect()
        self.AddLoadButton.pressed.connect(self.add_load)


class Aspy(QMainWindow):
    def __init__(self):
        super(Aspy, self).__init__()
        self.initUI()

    def initUI(self):
        self.statusBar().showMessage('Ready')

        ### Actions ###
        saveAct = QAction('Save current session', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.saveCurrentSession)

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
        self.setGeometry(200, 200, 1000, 600)
        self.setMinimumWidth(1000)
        self.show()

    def setDefaultLineType(self):
        pass

    def displayStatusMsg(self, args):
        self.statusBar().showMessage(args)

    def saveCurrentSession(self):
        print('save current session')

    def loadSession(self):
        print('load session')
        # try:
        #     self.CircuitInputer.setLayoutHidden(self.CircuitInputer.BarLayout, False)
        # except Exception:
        #     logging.error(traceback.format_exc())

    def addLineType(self):
        print('add line type')
        self.CircuitInputer.setLayoutHidden(self.CircuitInputer.InputNewLineType, False)

    def editLineType(self):
        print('edit line type')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    aspy = Aspy()
    sys.exit(app.exec_())