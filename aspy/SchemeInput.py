import logging
import sys
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import QPen, QPixmap, QBrush
from PyQt5.QtWidgets import *

from aspy.core import *


# TODO: Define store method for data in graph
# TODO: Interaction between outside and inside widget


N = 10  # grid size in schemeinputer
ID = 1  # 0 for slack bus
GRID_ELEMENTS = np.zeros((N, N), object)  # hold the aspy.core elements
BUSES_PIXMAP = np.zeros((N, N), object)  # hold the buses drawings
TL_PIXMAP = np.zeros((N, N), object)  # hold the transmission line drawing
BUSES = np.zeros((0,), object)  # hold the buses
TL = []  # hold the transmission lines
# TL = [[TL, coordinates], ]
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
        self.selector_radius = length/2
        self.SceneView = self.setSceneRect(0, 0, self._oneUnityLength*self.n, self._oneUnityLength*self.n)  # Visible portion of Scene to View
        self.quantizedInterface = self.getQuantizedInterface()
        self.showQuantizedInterface()


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
                    pixmap_coords = central_point.x()-self._oneUnityLength/2, central_point.y()-self._oneUnityLength/2
                    sceneItem.setPos(pixmap_coords[0], pixmap_coords[1])
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
                        self._methodSignal.emit_sig('showBarInspector')
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
                                    TL_PIXMAP[i, j] = line
                                    self._moveHistory[:, :] = -1
                                    self._lastRetainer = True  # Prevent the user for put line outside last bus
                                    self._pointerSignal.emit_sig((i, j))
                                    self._methodSignal.emit_sig('addLine')
                                elif not isinstance(GRID_ELEMENTS[i, j], Barra) and not (self._lastRetainer or self._firstRetainer):
                                    # started from a bus
                                    line = self.drawLine(self._moveHistory)
                                    TL_PIXMAP[i, j] = line
                                    self._moveHistory[:, :] = -1
                                    self._pointerSignal.emit_sig((i, j))
                                    self._methodSignal.emit_sig('addLine')
                            except Exception:
                                logging.error(traceback.format_exc())
                            # print(TL_PIXMAP)
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
        super(CircuitInputer, self).__init__(parent)
        ### General initializations ###
        self.Scene = SchemeInputer()
        self.View = QGraphicsView(self.Scene)
        self.SchemeInputLayout = QHBoxLayout()  # Layout for SchemeInput
        self.SchemeInputLayout.addWidget(self.View)
        self._currentObject = None  # coordinates to current object being manipuled
        self._startNewLine = True
        self._ltorigin = None
        try:
            self.__calls = {'addBus': self.add_bus,
                            'addLine': self.add_line,
                            'showBarInspector': self.showBarInspector,
                            'mouseReleased': self.startNewLine,
                            'storeOriginAddLt': self.storeOriginAddLt}
            self.Scene._pointerSignal.signal.connect(lambda args: self.setCurrentObject(args))
            self.Scene._methodSignal.signal.connect(lambda args: self.methodsCaller(args))
        except Exception:
            logging.error(traceback.format_exc())

        ### Inspector ###
        self.InspectorLayout = QVBoxLayout()  # Inspector
        self.TypeLayout = QHBoxLayout()
        self.TypeLayout.addStretch()
        self.TypeLayout.addStretch()
        self.InspectorLayout.addLayout(self.TypeLayout)

        ### Layout for general bar case ###
        self.BarLayout = QVBoxLayout()

        self.BarTitle = QLabel('Bar title')
        self.BarTitle.setAlignment(Qt.AlignCenter)

        self.BarV_Value = QLineEdit('0.0')
        self.BarV_Value.setEnabled(False)

        self.BarAngle_Value = QLineEdit('0.0º')
        self.BarAngle_Value.setEnabled(False)

        self.BarDataFormLayout = QFormLayout()
        self.BarDataFormLayout.addRow('|V|', self.BarV_Value)
        self.BarDataFormLayout.addRow('\u03b4', self.BarAngle_Value)

        self.AddGenerationLabel = QLabel('Geração')
        self.AddGenerationLabel.setAlignment(Qt.AlignCenter)
        self.AddGenerationButton = QPushButton('+')
        self.AddGenerationButton.pressed.connect(self.add_gen)  # Bind button to make input editable
        self.AddGenerationFormLayout = QFormLayout()  # Layout add generation
        self.AddLoadFormLayout = QFormLayout()
        self.PgInput = QLineEdit('0.0')
        self.QgInput = QLineEdit('0.0')
        self.PgInput.setEnabled(False); self.QgInput.setEnabled(False)
        self.AddGenerationFormLayout.addRow('Qg', self.QgInput)
        self.AddGenerationFormLayout.addRow('Pg', self.PgInput)

        self.AddLoadLabel = QLabel('Carga')
        self.AddLoadLabel.setAlignment(Qt.AlignCenter)
        self.AddLoadButton = QPushButton('+')
        self.AddLoadButton.pressed.connect(self.add_load)
        self.QlInput = QLineEdit('0.0')
        self.PlInput = QLineEdit('0.0')
        self.PlInput.setEnabled(False); self.QlInput.setEnabled(False)
        self.AddLoadFormLayout.addRow('Ql ', self.QlInput)
        self.AddLoadFormLayout.addRow('Pl ', self.PlInput)

        self.RemoveBus = QPushButton('Remove')
        self.RemoveBus.pressed.connect(self.remove_bus)

        self.RemoveTL = QPushButton('tirar tl')
        self.RemoveTL.pressed.connect(self.remove_line)

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
        self.BarLayout.addWidget(self.RemoveTL)

        # print(self.BarDataFormLayout.itemAt(1).widget())
        # TODO: bug here in ordering of widgets
        # self.BarLayoutFrame = QFrame()  # mask
        # self.BarLayoutFrame.setLayout(self.BarLayout)
        # self.BarLayoutFrame.hide()

        ### General Layout for LT case ###
        self.LtLayout = QVBoxLayout()

        ### Layout that holds bus inspector and Stretches ###
        self.InspectorAreaLayout = QVBoxLayout()
        self.InspectorAreaLayout.addStretch()
        self.InspectorAreaLayout.addLayout(self.InspectorLayout)
        self.InspectorAreaLayout.addLayout(self.BarLayout)
        # self.InspectorAreaLayout.addWidget(self.BarLayoutFrame)
        self.InspectorAreaLayout.addLayout(self.LtLayout)
        self.InspectorAreaLayout.addStretch()

        ### Toplayout ###
        self.TopLayout = QHBoxLayout()
        self.TopLayout.addLayout(self.InspectorAreaLayout)
        self.TopLayout.addLayout(self.SchemeInputLayout)
        self.setLayout(self.TopLayout)


    def storeOriginAddLt(self):
        if self._startNewLine:
            self._ltorigin = self._currentObject


    def add_line(self):
        global TL, TL_PIXMAP
        # args = [(i, j), line]
        # TL = [[TL, coordinates], ]
        try:
            if self._startNewLine:
                print('STARTING NEW LINE')
                NEW_TL = LT(origin=self._ltorigin)
                TL.append([NEW_TL, []])
                # print(TL[-1])
                TL[-1][1].append(self._ltorigin)
                TL[-1][1].append(self._currentObject)
            else:
                print('CONTINUING NEW LINE')
                CONTINUED_TL = TL[-1][0]
                CONTINUED_LT_COORDS = TL[-1][1]
                CONTINUED_LT_COORDS.append(self._currentObject)
                if isinstance(GRID_ELEMENTS[self._currentObject], Barra):
                    if CONTINUED_TL.destiny is None:
                        CONTINUED_TL.destiny = self._currentObject
            self._startNewLine = False
            print(TL[-1][0].origin, TL[-1][0].destiny)
            print(TL[-1][1])
        except Exception:
            logging.error(traceback.format_exc())


    def remove_line(self):
        try:
            RemovingTlPosition, RemovingTl = self.getLtPosFromGridPos(self._currentObject)
            print(RemovingTlPosition)
            for coord in RemovingTl[1][1:]:
                print('TL element >>> ', TL_PIXMAP[coord])
                self.Scene.removeItem(TL_PIXMAP[coord])
                # TL_PIXMAP[coord] = 0
            TL.remove(RemovingTl)
        except Exception:
            logging.error(traceback.format_exc())


    def startNewLine(self):
        self._startNewLine = True


    def methodsCaller(self, args):
        self.__calls[args]()


    def setCurrentObject(self, args):
        self._currentObject = args


    def updateBarInspector(self, BUS=0.0):
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


    def showBarInspector(self):
        # print('showBarInspector')
        BUS = GRID_ELEMENTS[self._currentObject]
        try:
            self.updateBarInspector(BUS)
        except Exception:
            print(logging.error(traceback.format_exc()))


    def add_bus(self):
        global GRID_ELEMENTS, ID, BUSES
        coords = self._currentObject
        if all([BUS.barra_id > 0 for BUS in BUSES]) or np.size(BUSES) == 0:
            # first add, or add after bus' exclusion
            SLACK = Barra(barra_id=0, posicao=coords)
            BUSES = np.insert(BUSES, 0, SLACK)
            GRID_ELEMENTS[coords] = SLACK
        elif any([BUS.barra_id == 0 for BUS in BUSES]) and np.size(BUSES) > 0:
            # sequenced bus insert
            BUS = Barra(barra_id=ID, posicao=coords)
            GRID_ELEMENTS[coords] = BUS
            BUSES = np.append(BUSES, BUS)
            ID += 1
        self.showBarInspector()


    def remove_bus(self):
        global ID, BUSES, GRID_ELEMENTS, BUSES_PIXMAP
        if GRID_ELEMENTS[self._currentObject]:
            POS, BUS = self.getBusFromGridEl(GRID_ELEMENTS[self._currentObject])
            if BUS.barra_id != 0:
                ID -= 1
                BUSES = np.delete(BUSES, POS)
                for i in range(1, ID):
                    BUSES[i].barra_id = i
            elif BUS.barra_id == 0:
                BUSES = np.delete(BUSES, POS)
            self.Scene.removeItem(BUSES_PIXMAP[self._currentObject])
            BUSES_PIXMAP[self._currentObject] = 0
            self.showBarInspector()


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
    def getLtPosFromGridPos(coords):
        """Returns the position in TL array, given the coordinates"""
        for pos, tl in enumerate(TL):
            if coords in tl[1]:
                return pos, tl


    def submit_gen(self):
        global GRID_ELEMENTS, BUSES
        print('>>> submit_gen')
        if isinstance(GRID_ELEMENTS[self._currentObject], Barra):
            GRID_ELEMENTS[self._currentObject].v = complex(self.BarV_Value.text())
            GRID_ELEMENTS[self._currentObject].pg = float(self.PgInput.text())
            POS, _ = self.getBusFromGridEl(GRID_ELEMENTS[self._currentObject])
            BUSES[POS].v = complex(self.BarV_Value.text())
            BUSES[POS].pg = float(self.PgInput.text())
            self.AddGenerationButton.setText('-')
            self.AddGenerationButton.disconnect()
            self.AddGenerationButton.pressed.connect(self.remove_gen)


    def remove_gen(self):
        global GRID_ELEMENTS, BUSES
        print('remove_gen')
        if isinstance(GRID_ELEMENTS[self._currentObject], Barra):
            GRID_ELEMENTS[self._currentObject].v = complex(0)
            GRID_ELEMENTS[self._currentObject].pg = 0.0
            POS, _ = self.getBusFromGridEl(GRID_ELEMENTS[self._currentObject])
            BUSES[POS].v = complex(0)
            BUSES[POS].pg = 0.0
            self.BarV_Value.setEnabled(False)
            self.PgInput.setEnabled(False)
            self.BarV_Value.setText(str(GRID_ELEMENTS[self._currentObject].v))
            self.PgInput.setText(str(GRID_ELEMENTS[self._currentObject].pg))
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CircuitInputer()
    ex.show()
    sys.exit(app.exec_())