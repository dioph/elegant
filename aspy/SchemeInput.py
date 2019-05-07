import logging
import sys
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import QPen, QPixmap, QBrush
from PyQt5.QtWidgets import *

from aspy.core import *


# TODO: first bar is always a slack bar
# TODO: Define store method for data in graph
# TODO: On scrolling, delete only the yellow squares


class SchemeInputer(QGraphicsScene):
    def __init__(self, n=10, length=50, *args, **kwargs):
        super(SchemeInputer, self).__init__(*args, **kwargs)
        self.n = n
        self._oneUnityLength = length
        # self._moveHistory = np.ones((2, 2)) * -1
        self._moveHistory = np.ones((2, 2))*-1
        # self._moveHistory[:-1, :] = -1; self._moveHistory[-1, :] = None
        self._selectorHistory = np.array([None, -1, -1])  # 0: old QRect, 1 & 2: coordinates to new QRect
        self._lastRetainer, self._firstRetainer = False, True
        self.SceneView = self.setSceneRect(0, 0, self._oneUnityLength*self.n, self._oneUnityLength*self.n)  # Visible portion of Scene to View
        self.selector_radius = length/2
        self.quantizedInterface = self.getQuantizedInterface()
        self.gridElements = np.zeros_like(self.quantizedInterface, object)
        print(self.quantizedInterface)
        self.showQuantizedInterface()


    @staticmethod
    def distance(interface_point, point):
        return np.sqrt((interface_point[0]-point.x())**2+(interface_point[1]-point.y())**2)


    def Point_pos(self, central_point):
        i = int((central_point.y()-self._oneUnityLength/2)/self._oneUnityLength)
        j = int((central_point.x()-self._oneUnityLength/2)/self._oneUnityLength)
        return i, j


    def mouseReleaseEvent(self, event):
        self._moveHistory[:, :] = -1
        self._lastRetainer = False
        self._firstRetainer = True
        # self._released = True
        # for i in range(np.shape(self._moveHistory)[0]):
        #     for j in range(np.shape(self._moveHistory)[1]):
        #         self._moveHistory[i, j] = -1

        # self._moveHistory[:-1, :] = -1; self._moveHistory[-1, :] = None


    def drawLine(self, coordinates):
        pen = QPen()
        pen.setWidth(2.5)
        self.addLine(coordinates[0, 0], coordinates[0, 1], coordinates[1, 0], coordinates[1, 1], pen)


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
        try:
            double_pressed = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                if self.distance(double_pressed, central_point) <= self.selector_radius:
                    i, j = self.Point_pos(central_point)
                    print(i, j)
                    self.gridElements[i, j] = Barra()
                    pixmap = QPixmap('./data/buttons/DOT.jpg')
                    pixmap = pixmap.scaled(self._oneUnityLength, self._oneUnityLength, Qt.KeepAspectRatio)
                    sceneItem = self.addPixmap(pixmap)
                    pixmap_coords = central_point.x()-self._oneUnityLength/2, central_point.y()-self._oneUnityLength/2
                    sceneItem.setPos(pixmap_coords[0], pixmap_coords[1])
        except Exception:
            logging.error(traceback.format_exc())


    def mousePressEvent(self, event):
        # L button: 1; R button: 2
        print('mouse button: ', event.button())
        if event.button() in (1, 2):
            pressed = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                if self.distance(pressed, central_point) <= self.selector_radius:
                    i, j = self.Point_pos(central_point)
                    self.clearSquare(self._selectorHistory[0])
                    #  catches up right corner
                    self._selectorHistory[1] = central_point.x() - self._oneUnityLength/2
                    self._selectorHistory[2] = central_point.y() - self._oneUnityLength/2
                    self._selectorHistory[0] = self.drawSquare(self._selectorHistory[1:])
                    # print('currentRect: ', self._selectorHistory[0])


    def sceneRectChanged(self, QRectF):
        pass


    def mouseMoveEvent(self, event):
        """This method gives behavior to wire tool"""
        clicked = event.scenePos().x(), event.scenePos().y()
        if event.button() == 0:
            for central_point in self.quantizedInterface.flatten():
                i, j = self.Point_pos(central_point)
                try:
                    if self.distance(clicked, central_point) <= self.selector_radius:
                        if np.all(self._moveHistory[0] < 0):  # Set source
                            self._moveHistory[0, 0] = central_point.x()
                            self._moveHistory[0, 1] = central_point.y()
                            if isinstance(self.gridElements[i, j], Barra):
                                self._firstRetainer = False
                        if central_point.x() != self._moveHistory[0, 0] \
                                or central_point.y() != self._moveHistory[0, 1]:  # Set destiny
                            self._moveHistory[1, 0] = central_point.x()
                            self._moveHistory[1, 1] = central_point.y()
                        if (np.all(self._moveHistory > 0)) and \
                                (np.any(self._moveHistory[0, :] != np.any(self._moveHistory[1, :]))):
                            ### DRAW LINE ###
                            if isinstance(self.gridElements[i, j], Barra) and (not self._lastRetainer and not self._firstRetainer):
                                print('break on next move')
                                self.drawLine(self._moveHistory)  # Draw the line
                                self._moveHistory[:, :] = -1  # Reset _moveHistory
                                self._lastRetainer = True  # Prevent the user for put line outside last bus
                            if not isinstance(self.gridElements[i, j], Barra) and (not self._lastRetainer and not self._firstRetainer):
                                print('do anything')
                                self.drawLine(self._moveHistory)  # Draw the line
                                self._moveHistory[:, :] = -1  # Reset _moveHistory
                            else:
                                pass
                    else:  # No bar case
                        pass
                    print(self._moveHistory)
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
        self.scene = SchemeInputer()
        self.view = QGraphicsView(self.scene)
        self.SchemeInputLayout = QHBoxLayout()  # Layout for SchemeInput
        self.SchemeInputLayout.addWidget(self.view)

        ### Inspector ###
        self.InspectorLayout = QVBoxLayout()  # Inspector
        self.TypeLayout = QHBoxLayout()
        self.TypeLayout.addStretch()
        self.TypeLayout.addStretch()
        self.InspectorLayout.addLayout(self.TypeLayout)

        ### General Layout for general bar case ###
        self.BarLayout = QVBoxLayout()

        self.BarTitle = QLabel('Bar title')
        # self.BarTitle.setStyleSheet("QLabel {font_size: 20}")
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
        # self.AddLoadFormLayout.setGeometry(0)

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

        ### General Layout for LT case ###
        self.LtLayout = QVBoxLayout()

        ### Layout that holds Inspector and Stretches ###
        self.InspectorAreaLayout = QVBoxLayout()
        self.InspectorAreaLayout.addStretch()
        self.InspectorAreaLayout.addLayout(self.InspectorLayout)
        self.InspectorAreaLayout.addLayout(self.BarLayout)
        self.InspectorAreaLayout.addLayout(self.LtLayout)
        self.InspectorAreaLayout.addStretch()

        ### Toplayout ###
        self.TopLayout = QHBoxLayout()
        self.TopLayout.addLayout(self.InspectorAreaLayout)
        self.TopLayout.addLayout(self.SchemeInputLayout)
        self.setLayout(self.TopLayout)


    def add_gen(self):
        print('add_gen')
        self.BarV_Value.setEnabled(True)
        self.PgInput.setEnabled(True)
        self.AddGenerationButton.setText('OK')
        self.AddGenerationButton.disconnect()
        self.AddGenerationButton.pressed.connect(self.submit_gen)


    def submit_gen(self):
        print('submit_gen')
        self.AddGenerationButton.setText('-')
        self.AddGenerationButton.disconnect()
        self.AddGenerationButton.pressed.connect(self.remove_gen)


    def remove_gen(self):
        print('remove_gen')
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