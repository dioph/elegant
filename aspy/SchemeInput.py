import sys
import traceback
import logging


import numpy
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPen, QPixmap, QBrush

from aspy.core import *


# TODO: circles in grid
# TODO: Define store method for data in graph
# TODO: Insert line only between two bars
# TODO: On scrolling, delete only the yellow squares


class SchemeInputer(QGraphicsScene):
    def __init__(self, n=10, length=50, *args, **kwargs):
        super(SchemeInputer, self).__init__(*args, **kwargs)
        self.n = n
        self._oneUnityLength = length
        self._cursorHistory = numpy.ones((2, 2)) * -1
        self._selectorHistory = numpy.array([None, -1, -1])  # 0: old QRect, 1 & 2: coordinates to new QRect
        self.SceneView = self.setSceneRect(0, 0, self._oneUnityLength*self.n, self._oneUnityLength*self.n)  # Visible portion of Scene to View
        self.selector_radius = length/2
        self.quantizedInterface = self.getQuantizedInterface()
        self.elementsGrid = numpy.zeros_like(self.quantizedInterface, object)
        self.showQuantizedInterface()


    @staticmethod
    def distance(interface_point, point):
        return numpy.sqrt((interface_point[0]-point.x())**2+(interface_point[1]-point.y())**2)


    def mouseReleaseEvent(self, event):
        for i in range(numpy.shape(self._cursorHistory)[0]):
            for j in range(numpy.shape(self._cursorHistory)[1]):
                self._cursorHistory[i, j] = -1


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
        # print('oldRect: ', oldQRect)
        # TODO: bug in clearing square after scrolling in any direction
        if oldQRect is not None:
            self.removeItem(oldQRect)


    def mouseDoubleClickEvent(self, event):
        try:
            double_pressed = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                if self.distance(double_pressed, central_point) <= self.selector_radius:
                    pixmap = QPixmap('./data/buttons/DOT.jpg')
                    pixmap = pixmap.scaled(self._oneUnityLength, self._oneUnityLength, Qt.KeepAspectRatio)
                    sceneItem = self.addPixmap(pixmap)
                    pixmap_coords = central_point.x()-self._oneUnityLength/2, central_point.y()-self._oneUnityLength/2
                    sceneItem.setPos(pixmap_coords[0], pixmap_coords[1])
                    # print('added element')
        except Exception:
            logging.error(traceback.format_exc())


    def mousePressEvent(self, event):
        # L button: 1; R button: 2
        print('mouse button: ', event.button())
        if event.button() in (1, 2):
            pressed = event.scenePos().x(), event.scenePos().y()
            for central_point in self.quantizedInterface.flatten():
                if self.distance(pressed, central_point) <= self.selector_radius:
                    self.clearSquare(self._selectorHistory[0])
                    #  catches up right corner
                    self._selectorHistory[1] = central_point.x() - self._oneUnityLength/2
                    self._selectorHistory[2] = central_point.y() - self._oneUnityLength/2
                    self._selectorHistory[0] = self.drawSquare(self._selectorHistory[1:])
                    # print('currentRect: ', self._selectorHistory[0])


    def sceneRectChanged(self, QRectF):
        pass

    def mouseMoveEvent(self, event):
        """Give behavior to wire tool"""
        clicked = event.scenePos().x(), event.scenePos().y()
        # print(event.button())
        if event.button() == 0:
            for central_point in self.quantizedInterface.flatten():
                try:
                    if self.distance(clicked, central_point) <= self.selector_radius:
                        if numpy.all(self._cursorHistory[0] < 0):  # No source
                            self._cursorHistory[0, 0] = central_point.x()
                            self._cursorHistory[0, 1] = central_point.y()
                        if central_point.x() != self._cursorHistory[0, 0] or central_point.y() != self._cursorHistory[0, 1]:  # Set destiny
                            self._cursorHistory[1, 0] = central_point.x()
                            self._cursorHistory[1, 1] = central_point.y()
                        if (numpy.all(self._cursorHistory > 0)) and (numpy.any(self._cursorHistory[0, :] != numpy.any(self._cursorHistory[1, :]))):
                            # print('DEBUG >>> scrolling is drawing lines. _cursorHistory: ', self._cursorHistory)
                            self.drawLine(self._cursorHistory)  # Draw the line
                            for i in range(numpy.shape(self._cursorHistory)[0]):  # Reset _historyCursor
                                for j in range(numpy.shape(self._cursorHistory)[1]):
                                    self._cursorHistory[i, j] = -1
                except Exception:
                    logging.error(traceback.format_exc())


    def getQuantizedInterface(self):
        quantizedInterface = numpy.zeros((self.n, self.n), tuple)
        width, height = self.width(), self.height()
        for i in range(self.n):
            for j in range(self.n):
                quantizedInterface[i, j] = QPoint(width/(2*self.n) + i*width/self.n, height/(2*self.n) + j*height/self.n)
        return quantizedInterface


    def showQuantizedInterface(self):
        #  (0, 0) is upper left corner
        width, height = self.width(), self.height()
        spacing_x, spacing_y = width/self.n, height/self.n
        quantized_x, quantized_y = numpy.arange(0, width, spacing_x), numpy.arange(0, height, spacing_y)
        pen = QPen()
        pen.setColor(Qt.lightGray)
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

        # self.ElementSelectorButtonsLayout = QGridLayout()  # Layout for ToggleButtons
        # self.PushButtonTrafo = QPushButton('Trafo')
        # self.PushButtonLT = QPushButton('Linha de transmissão')
        # self.PushButtonBarra = QPushButton('Barra')
        # # self.PushButtonPQ = QPushButton('Barra PQ')
        # self.ElementSelectorButtonsLayout.addWidget(self.PushButtonTrafo, 1, 1)
        # self.ElementSelectorButtonsLayout.addWidget(self.PushButtonLT, 2, 1)
        # self.ElementSelectorButtonsLayout.addWidget(self.PushButtonBarra, 3, 1)
        # self.ElementSelectorButtonsLayout.addWidget(self.PushButtonPQ, 4, 1)

        ### Inspector ###
        self.InspectorLayout = QVBoxLayout()  # Inspector
        self.TypeLayout = QHBoxLayout()
        # self.isBar = QRadioButton('Bar'); self.isLT = QRadioButton('Lt'); self.isTrafo = QRadioButton('Trafo')
        # self.isBar.toggled.connect(lambda: self.defineElementType(self.isBar))
        # self.isLT.toggled.connect(lambda: self.defineElementType(self.isLT))
        # self.isTrafo.toggled.connect(lambda: self.defineElementType(self.isTrafo))
        self.TypeLayout.addStretch()
        # self.TypeLayout.addWidget(self.isBar); self.TypeLayout.addWidget(self.isLT); self.TypeLayout.addWidget(self.isTrafo)
        self.TypeLayout.addStretch()
        self.InspectorLayout.addLayout(self.TypeLayout)

        ### General Layout for general bar case ###
        self.BarLayout = QVBoxLayout()
        self.BarName = QLabel('Bar title')
        self.BarName.setAlignment(Qt.AlignCenter)
        self.BarV = QLabel('|V| = 1.0')
        self.BarV.setAlignment(Qt.AlignCenter)
        self.BarAngle = QLabel('\u03b4 = 45º')
        self.BarAngle.setAlignment(Qt.AlignCenter)
        self.AddGenerationLabel = QLabel('Geração')
        self.AddGenerationLabel.setAlignment(Qt.AlignCenter)
        self.AddGenerationButton = QPushButton('+')
        self.AddGenerationButton.pressed.connect(self.addGeneration)  # Bind button to make input editable
        self.AddGenerationFormLayout = QFormLayout()
        self.AddLoadFormLayout = QFormLayout()
        self.PgInput = QLineEdit()
        self.QgInput = QLineEdit()
        self.PgInput.setEnabled(False); self.QgInput.setEnabled(False)
        self.AddGenerationFormLayout.addRow('Qg', self.QgInput)
        self.AddGenerationFormLayout.addRow('Pg', self.PgInput)

        self.AddLoadLabel = QLabel('Carga')
        self.AddLoadLabel.setAlignment(Qt.AlignCenter)
        self.AddLoadButton = QPushButton('+')
        self.AddLoadButton.pressed.connect(self.addLoad)
        self.QlInput = QLineEdit()
        self.PlInput = QLineEdit()
        self.PlInput.setEnabled(False); self.QlInput.setEnabled(False)
        self.AddLoadFormLayout.addRow('Ql ', self.QlInput)
        self.AddLoadFormLayout.addRow('Pl ', self.PlInput)

        self.BarLayout.addWidget(self.BarName)
        self.BarLayout.addWidget(self.BarV)
        self.BarLayout.addWidget(self.BarAngle)
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

    def addGeneration(self):
        self.PgInput.setEnabled(True)
        self.QgInput.setEnabled(True)

    def addLoad(self):
        self.PlInput.setEnabled(True)
        self.QlInput.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CircuitInputer()
    ex.show()
    sys.exit(app.exec_())