import logging
import sys
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from aspy.core import *

N = 20  # grid size in schemeinputer
ID = 1  # 0 for slack bus
GRID_ELEMENTS = np.zeros((N, N), object)  # hold the aspy.core elements
BUSES_PIXMAP = np.zeros((N, N), object)  # hold the buses drawings
BUSES = np.zeros((0,), object)  # hold the buses
TL = []  # hold the transmission lines
# hold the types of transmission lines
LINE_TYPES = [['Default', {'l': 80.0, 'r': 1.0, 'd12': 1.0, 'd23': 1.0, 'd31': 1.0, 'd': 1.0, 'rho': 1.78e-8, 'm': 1}]]
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
        self._startNewLT = True
        self._ltorigin = None
        self._temp = None
        self._statusMsg = GenericSignal()
        self.__calls = {'addBus': self.add_bus,
                        'addLine': self.add_line,
                        'showInspector': self.showInspector,
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

        ### Line edit to input bus Pg ###
        self.PgInput = QLineEdit('0.0')
        self.PgInput.setEnabled(False)
        self.PgInput.setValidator(QDoubleValidator(0.0, 100.0, 2))

        ### Line edit to input bus Qg ###
        self.QgInput = QLineEdit('0.0')
        self.QgInput.setEnabled(False)
        self.QgInput.setValidator(QDoubleValidator(0.0, 100.0, 2))

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

        # self.chooseParameters = QRadioButton('Parameters')
        # self.chooseParameters.toggled.connect(self.chooseNewLineTypeInputManner)
        # self.chooseImpedance = QRadioButton('Impedance')
        # self.chooseImpedance.toggled.connect(self.chooseNewLineTypeInputManner)
        # self.chooseLayout = QHBoxLayout()
        # self.chooseLayout.addWidget(self.chooseParameters)
        # self.chooseLayout.addWidget(self.chooseImpedance)

        self.ModelName = QLineEdit()

        # self.YLineEdit = QLineEdit()
        # self.ZLineEdit = QLineEdit()

        self.RhoLineEdit = QLineEdit()
        self.RhoLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.EllLineEdit = QLineEdit()
        self.EllLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))
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
        # self.InputNewLineTypeFormLayout.addRow('Y', self.YLineEdit)
        # self.InputNewLineTypeFormLayout.addRow('Z', self.ZLineEdit)
        self.InputNewLineTypeFormLayout.addRow('\u03c1', self.RhoLineEdit)
        self.InputNewLineTypeFormLayout.addRow('\u2113', self.EllLineEdit)
        self.InputNewLineTypeFormLayout.addRow('r', self.rLineEdit)
        self.InputNewLineTypeFormLayout.addRow('d12', self.d12LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d23', self.d23LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d31', self.d31LineEdit)
        self.InputNewLineTypeFormLayout.addRow('d', self.dLineEdit)
        self.InputNewLineTypeFormLayout.addRow('m', self.mLineEdit)

        self.InputNewLineType.addStretch()
        # self.InputNewLineType.addLayout(self.chooseLayout)
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

        self.chooseLtFormLayout = QFormLayout()

        self.chooseLtModel = QComboBox()
        self.chooseLtModel.currentIndexChanged.connect(self.updateLtParameters)

        self.LtZLineEdit = QLineEdit()
        self.LtZLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))

        self.LtYLineEdit = QLineEdit()
        self.LtYLineEdit.setValidator(QDoubleValidator(0.0, 100.0, 2))

        self.chooseLtFormLayout.addRow('Model', self.chooseLtModel)
        self.chooseLtFormLayout.addRow('Z', self.LtZLineEdit)
        self.chooseLtFormLayout.addRow('Y', self.LtYLineEdit)

        self.removeLTPushButton = QPushButton('Remove LT')
        self.removeLTPushButton.setMinimumWidth(200.0)
        self.removeLTPushButton.pressed.connect(self.remove_selected_line)
        # self.chooseLtFormLayout.addRow('', self.removeLTPushButton)

        self.chooseTrafoFormLayout = QFormLayout()
        self.XTrafoLineEdit = QLineEdit()
        self.VNom1LineEdit = QLineEdit()
        self.VNom2LineEdit = QLineEdit()

        self.generalLtOrTrafoSubmitPushButton = QPushButton('Submit')
        self.generalLtOrTrafoSubmitPushButton.setMinimumWidth(200)

        self.chooseTrafoFormLayout.addRow('X', self.XTrafoLineEdit)
        self.chooseTrafoFormLayout.addRow('VNom 1', self.VNom1LineEdit)
        self.chooseTrafoFormLayout.addRow('VNom 2', self.VNom2LineEdit)
        # self.chooseTrafoFormLayout.addRow('', self.generalLtOrTrafoSubmitPushButton)

        self.LtOrTrafoLayout.addLayout(self.chooseLtOrTrafo)
        self.LtOrTrafoLayout.addLayout(self.chooseLtFormLayout)
        self.LtOrTrafoLayout.addLayout(self.chooseTrafoFormLayout)
        # Buttons submit e remove
        self.LtOrTrafoLayout.addWidget(self.removeLTPushButton)
        self.LtOrTrafoLayout.addWidget(self.generalLtOrTrafoSubmitPushButton)

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
                self.setLayoutHidden(self.chooseLtFormLayout, False)
                self.setLayoutHidden(self.chooseTrafoFormLayout, True)
                self.removeLTPushButton.setHidden(False)
                self.generalLtOrTrafoSubmitPushButton.setHidden(False)
                self.generalLtOrTrafoSubmitPushButton.disconnect()
                self.generalLtOrTrafoSubmitPushButton.pressed.connect(self.updateLtParameters)
            elif self.chooseTrafo.isChecked():
                self.setLayoutHidden(self.chooseLtFormLayout, True)
                self.setLayoutHidden(self.chooseTrafoFormLayout, False)
                self.removeLTPushButton.setHidden(True)
                self.generalLtOrTrafoSubmitPushButton.setHidden(False)
                self.generalLtOrTrafoSubmitPushButton.disconnect()
                self.generalLtOrTrafoSubmitPushButton.pressed.connect(self.add_trafo)


    def updateLtInspector(self):
        '''
        ------------------------
        Called by: showInspector
        ------------------------
        '''
        try:
            self.chooseLtModel.addItem(LINE_TYPES[-1][0])  # Adding name to ComboBox
        except Exception:
            logging.error(traceback.format_exc())


    def updateLtParameters(self):
        print('updateLtParameters')

    # def chooseNewLineTypeInputManner(self):
    #     layout = self.InputNewLineTypeFormLayout
    #     linedits = list(layout.itemAt(i).widget() for i in range(layout.count()) \
    #                     if isinstance(layout.itemAt(i).widget(), QLineEdit))
    #     if self.chooseImpedance.isChecked():
    #         for linedit in linedits[3:]:
    #             linedit.setEnabled(False)
    #             linedit.setText('')
    #         for linedit in linedits[1:3]:
    #             linedit.setEnabled(True)
    #     else:
    #         for linedit in linedits[3:]:
    #             linedit.setEnabled(True)
    #         for linedit in linedits[1:3]:
    #             linedit.setEnabled(False)
    #             linedit.setText('')


    ### NEW VERSION ###
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
                LINE_TYPES.append([titles[1], {par_names[i]: par_values[i] for i in range(len(par_names))}])
                self._statusMsg.emit_sig('The model has been stored')
        except Exception:
            logging.error(traceback.format_exc())
        finally:
            print(LINE_TYPES)


    ### OLD VERSION ###
    # def addNewLineType(self):
    #     global LINE_TYPES
    #     layout = self.InputNewLineTypeFormLayout
    #     new_values = list(layout.itemAt(i).widget().text() for i in range(layout.count()) \
    #                       if not isinstance(layout.itemAt(i), QLayout))
    #     name = new_values[1] if new_values[1] != '' else 'model {}'.format(len(LINE_TYPES)+1)
    #     name_values_par = new_values[6::2]; name_values_imp = new_values[2:6:2]
    #     number_values_imp = new_values[3:7:2]; number_values_par = new_values[7::2]
    #     try:
    #         if all(map(lambda x: x[0] != name, LINE_TYPES)):
    #             if all(map(lambda x: x != '', number_values_imp)):
    #                 filtered = list(filter(lambda array: len(list(array[1].values())) == 2, LINE_TYPES))
    #                 if all(list(map(lambda x: float(x), number_values_imp)) != list(type[1].values()) for type in filtered):
    #                     LINE_TYPES.append([name, {name_values_imp[i]: float(number_values_imp[i]) \
    #                                               for i in range(len(number_values_imp))}])
    #                     self._statusMsg.emit_sig('Model recorded')
    #                 else:
    #                     self._statusMsg.emit_sig('This model has been already stored')
    #             elif all(map(lambda x: x != '', number_values_par)):
    #                 filtered = list(filter(lambda array: len(list(array[1].values())) == 8, LINE_TYPES))
    #                 if all(list(map(lambda x: float(x), number_values_par)) != list(type[1].values()) for type in filtered):
    #                     LINE_TYPES.append([name, {name_values_par[i]: float(number_values_par[i]) \
    #                                               for i in range(len(number_values_par))}])
    #                     self._statusMsg.emit_sig('Model recorded')
    #                 else:
    #                     self._statusMsg.emit_sig('This model has been already stored')
    #             self.setLayoutHidden(self.InputNewLineType, True)
    #             print(LINE_TYPES)
    #         else:
    #             self._statusMsg.emit_sig('The specified name already exists. Input another name for model')
    #     except Exception as exc:
    #         print(exc)
    #         self._statusMsg.emit_sig('Invalid input catched: you must input only float numbers')
    #     except Exception:
    #         logging.error(traceback.format_exc())


    def hideSpacer(self):
        self.Spacer.changeSize(0, 0)


    def showSpacer(self):
        self.Spacer.changeSize(200, 0)


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
        if self._startNewLT:
            self._ltorigin = self._currentElement


    def add_trafo(self):
        print('add_trafo')


    def add_line(self):
        global TL
        # args = [(i, j), line]
        # TL = [[TL, line, coordinates, bool ToExclude, ]
        try:
            if self._startNewLT:
                print('Colocando nova linha\n')
                NEW_TL = LT(origin=self._ltorigin)
                if not self.checkTlCrossing():
                    TL.append([NEW_TL, [], [], False])
                else:
                    print('Linha cruzou na saída')
                    TL.append([NEW_TL, [], [], True])
                TL[-1][1].append(self._temp)
                TL[-1][2].append(self._ltorigin)
                TL[-1][2].append(self._currentElement)
            else:
                print('Continuando linha\n')
                if self.checkTlCrossing():
                    TL[-1][3] = True
                    print('Linha cruzou com alguma outra já existente')
                TL[-1][1].append(self._temp)
                TL[-1][2].append(self._currentElement)
                if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                    if TL[-1][0].destiny is None:
                        TL[-1][0].destiny = self._currentElement
            self._startNewLT = False
        except Exception:
            logging.error(traceback.format_exc())


    def checkTlCrossing(self):
        for tl in TL:
            if self._currentElement in tl[2] and not isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                return True
            else:
                continue
        return False


    def remove_selected_line(self):
        pos, lt = self.getLtFromGridPos(self._currentElement)
        for linedrawing in lt[1]:
            self.Scene.removeItem(linedrawing)
        TL.remove(lt)
        print('len(TL) = ', len(TL))
        self.showInspector()


    def remove_pointless_lines(self):
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
        # Ter certeza que a última ação foi uma inserção de linha!
        global TL
        self._startNewLT = True
        try:
            if TL:
                if len(TL[-1][2]) == 2:  # Se a linha é composta por dois pontos
                    if not self.isLastLineDuplicated():  # Se a linha não está duplicada
                        # print('Segundo TL[-1]: ', TL[-1])
                        if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                            # Se o cursor está em cima de uma barra e a linha não tem destino
                            # print('>>> Setar destino:\n', TL)
                            TL[-1][0].destiny = GRID_ELEMENTS[self._currentElement]
                            # A linha recebe a barra como destino
                        elif not isinstance(GRID_ELEMENTS[self._currentElement], Barra) and TL[-1][0].destiny is None:
                            TL[-1][3] = True
                    else:  # Se a linha está duplicada
                        # print('Linha duplicada')
                        TL[-1][3] = True  # Será excluída
                else:  # Se a linha é composta por mais de dois pontos
                    if TL[-1][0].destiny is None:  # Se a linha não tiver destino
                        TL[-1][3] = True  # Será excluída
                    # De add_line, a linha True ou False se cruzar com alguma outra linha
            self.remove_pointless_lines()
            print('len(TL) = ', len(TL))
            for lt in TL:
                assert(lt[0].origin is not None)
                assert(lt[0].destiny is not None)
            if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                self.showInspector()
            else:
                self.showInspector()
        except Exception:
            logging.error(traceback.format_exc())


    def methodsTrigger(self, args):
        self.__calls[args]()


    def setCurrentObject(self, args):
        self._currentElement = args


    def updateBusInspector(self, BUS=0):
        """Updates the BI with bus data if bus existes or
        show that there's no bus (only after bus exclusion)
        ---------------------------------------------------
        Called by: showInspector, remove_gen
        """
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
        """Hide or show specific layouts, based on the current element
        or passed parameters by trigger methods
        --------------------------------------------------------------
        Called by: doAfterMouseRelease (after input), add_bus
        -----------------------------------------------------
        """
        try:
            # Even if there are two elements in a same square, only one will be identified
            pos_bus, bus = self.getBusFromGridPos(self._currentElement)
            pos_lt, lt = self.getLtFromGridPos(self._currentElement)
            pos_trafo, trafo = self.getTrafoFromGridPos(self._currentElement)

            if bus is not None:
                self.hideSpacer()
                self.setLayoutHidden(self.LtOrTrafoLayout, True)
                self.setLayoutHidden(self.BarLayout, False)
                self.updateBusInspector(self.getBusFromGridPos(self._currentElement)[1])
            elif lt is not None:
                assert trafo is None
                self.hideSpacer()
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, False)
                self.chooseLt.setChecked(True)
                self.setLayoutHidden(self.chooseTrafoFormLayout, True)
                self.setLayoutHidden(self.chooseLtFormLayout, False)
                self.generalLtOrTrafoSubmitPushButton.setHidden(False)
                self.removeLTPushButton.setHidden(False)
            elif trafo is not None:
                assert lt is None
                self.hideSpacer()
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, False)
                self.chooseTrafo.setChecked(True)
                self.setLayoutHidden(self.chooseTrafoFormLayout, False)
                self.setLayoutHidden(self.chooseLtFormLayout, True)
                self.generalLtOrTrafoSubmitPushButton.setHidden(False)
                self.removeLTPushButton.setHidden(False)
            else:
                # No element case
                self.setLayoutHidden(self.BarLayout, True)
                self.setLayoutHidden(self.LtOrTrafoLayout, True)
                self.showSpacer()
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
            POS, BUS = self.getBusFromGridPos(self._currentElement)
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
            self.updateBusInspector(self.getBusFromGridPos(self._currentElement)[1])
            self.showInspector()


    def add_gen(self):
        """
        Adds generation to the bus, desblocks some QLineEdits
        -----------------------------------------------------
        Called by: QPushButton Add generation (__init__)
        """
        try:
            global BUSES
            self.BarV_Value.setEnabled(True)
            self.PgInput.setEnabled(True)
            self.AddGenerationButton.setText('OK')
            self._statusMsg.emit_sig('Input generation data...')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.submit_gen)
        except Exception:
            logging.error(traceback.format_exc())


    @staticmethod
    def getBusFromGridPos(COORDS):
        """Returns the position in BUSES array and the BUS itself, given an bus from GRID_ELEMENT"""
        GRID_BUS = GRID_ELEMENTS[COORDS]
        if isinstance(GRID_BUS, Barra):
            for POS, BUS in enumerate(BUSES):
                if BUS.posicao == GRID_BUS.posicao:
                    return POS, BUS
                else:
                    continue
        return None, None


    @staticmethod
    def getLtFromGridPos(COORDS):
        """Returns the TL's position (in TL) and TL element, given the grid coordinates"""
        for pos, tl in enumerate(TL):
            if COORDS in tl[2]:
                return pos, tl
            else:
                continue
        return None, None


    @staticmethod
    def getTrafoFromGridPos(COORDS):
        """Returns the TRAFO'S position (in TRAFOS) and TRAFO element, given the grid coordinates"""
        for pos, trafo in enumerate(TRANSFORMERS):
            if COORDS in trafo[2]:
                return pos, trafo
            else:
                continue
        return None, None


    def submit_gen(self):
        """Updates bus parameters with the user input in BI
        ---------------------------------------------------
        Called by: add_gen (button rebind)
        ----------------------------------
        """
        global GRID_ELEMENTS, BUSES
        if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
            POS, _ = self.getBusFromGridPos(self._currentElement)
            BUSES[POS].v = float(self.BarV_Value.text())
            BUSES[POS].pg = float(self.PgInput.text())
            GRID_ELEMENTS[self._currentElement].v = BUSES[POS].v
            GRID_ELEMENTS[self._currentElement].pg = BUSES[POS].pg
            self._statusMsg.emit_sig('Added generation')
            print('Barra atualizada')
            print('V da barra: {0}, Pg da barra: {1}'.format(BUSES[POS].v, BUSES[POS].pg))
            self.BarV_Value.setEnabled(False)
            self.PgInput.setEnabled(False)
            self.AddGenerationButton.setText('-')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.remove_gen)


    def remove_gen(self):
        global GRID_ELEMENTS, BUSES
        if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
            POS, _ = self.getBusFromGridPos(self._currentElement)
            BUSES[POS].v = 0.0
            BUSES[POS].pg = 0.0
            GRID_ELEMENTS[self._currentElement].v = 0.0
            GRID_ELEMENTS[self._currentElement].pg = 0.0
            self._statusMsg.emit_sig('Removed generation')
            print('Geração removida')
            print('V da barra: {0}, Pg da barra: {1}'.format(BUSES[POS].v, BUSES[POS].pg))
            self.updateBusInspector(BUSES[POS])
            self.AddGenerationButton.setText('+')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.add_gen)


    def add_load(self):
        """
        ------------------------------------------
        Called by: QPushButton Add load (__init__)
        ------------------------------------------
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
        global GRID_ELEMENTS, BUSES
        try:
            if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                POS, _ = self.getBusFromGridPos(self._currentElement)
                BUSES[POS].pl = float(self.PlInput.text())
                BUSES[POS].ql = float(self.QlInput.text())
                GRID_ELEMENTS[self._currentElement].pl = BUSES[POS].pl
                GRID_ELEMENTS[self._currentElement].ql = BUSES[POS].ql
                self._statusMsg.emit_sig('Added load')
                print('Barra atualizada')
                print('Pl da barra: {0}, Ql da barra: {1}'.format(BUSES[POS].pl, BUSES[POS].ql))
                self.PlInput.setEnabled(False)
                self.QlInput.setEnabled(False)
                self.AddLoadButton.setText('-')
                self.AddLoadButton.disconnect()
                self.AddLoadButton.pressed.connect(self.remove_load)
        except Exception:
            logging.error(traceback.format_exc())

    def remove_load(self):
        try:
            global GRID_ELEMENTS, BUSES
            if isinstance(GRID_ELEMENTS[self._currentElement], Barra):
                POS, _ = getBusFromGridPos(self._currentElement)
                BUSES[POS].pl = 0.0
                BUSES[POS].ql = 0.0
                GRID_ELEMENTS[self._currentElement].pl = 0.0
                GRID_ELEMENTS[self._currentElement].ql = 0.0
                self._statusMsg.emit_sig('Removed load')
                print('Carga removida')
                print('Pl da barra: {0}, Ql da barra: {1}'.format(BUSES[POS].pl, BUSES[POS].ql))
                self.updateBusInspector(BUSES[POS])
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
        self.setGeometry(50, 50, 1000, 600)
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