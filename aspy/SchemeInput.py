import sys
import traceback
import logging

import numpy
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton,\
    QApplication, QGraphicsView, QGraphicsScene, QGridLayout
from PyQt5.QtGui import QPen, QPixmap, QBrush

from aspy.core import *


# TODO: circles in grid
# TODO: Define store method for data in graph
# TODO: Insert bar, doubleclick - QPixMap?
# TODO: Insert line only between two bars


class SchemeInputer(QGraphicsScene):
    def __init__(self, n=25, *args, **kwargs):
        super(SchemeInputer, self).__init__(*args, **kwargs)
        self.n = n
        self.setSceneRect(0, 0, 50*self.n, 50*self.n)  # Visible portion of Scene to View
        self.selector_radius = 25.0
        self._oneUnityLength = 50.0
        self.quantizedInterface = self.getQuantizedInterface()
        self._cursorHistory = numpy.ones((2, 2)) * -1
        self._selectorHistory = numpy.array([None, -1, -1])  # 0: old QRect, 1 & 2: coordinates to new QRect
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
        brush.setStyle(Qt.SolidPattern)
        x, y = coordinates
        QRect = self.addRect(x, y, self._oneUnityLength, self._oneUnityLength, pen, brush)
        return QRect


    def clearSquare(self, oldQRect):
        if oldQRect is not None:
            self.removeItem(oldQRect)


    def mousePressEvent(self, event):
        pressed = event.scenePos().x(), event.scenePos().y()
        for central_point in self.quantizedInterface.flatten():
            if self.distance(pressed, central_point) <= self.selector_radius:
                self.clearSquare(self._selectorHistory[0])
                #  catches up right corner
                self._selectorHistory[1] = central_point.x() - self._oneUnityLength/2
                self._selectorHistory[2] = central_point.y() - self._oneUnityLength/2
                self._selectorHistory[0] = self.drawSquare(self._selectorHistory[1:])


    def mouseMoveEvent(self, event):
        """Give behavior to wire tool"""
        clicked = event.scenePos().x(), event.scenePos().y()
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
                        self.drawLine(self._cursorHistory)  # Draw the line
                        for i in range(numpy.shape(self._cursorHistory)[0]):  # Reset _historyCursor
                            for j in range(numpy.shape(self._cursorHistory)[1]):
                                self._cursorHistory[i, j] = -1
            except Exception as e:
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


    def on_changed(self):
        """Updates grid spacing when window has been resized"""
        pass


class CircuitInputer(QWidget):
    def __init__(self, Viewer, parent=None):
        super(CircuitInputer, self).__init__(parent)
        self.Viewer = Viewer  # SchemeInput Viewer
        self.SchemeInputLayout = QHBoxLayout()  # Layout for SchemeInput
        self.SchemeInputLayout.addWidget(Viewer)

        self.ElementSelectorButtonsLayout = QGridLayout()  # Layout for ToggleButtons
        self.PushButtonTrafo = QPushButton('Trafo')
        self.PushButtonLT = QPushButton('Linha de transmissão')
        self.PushButtonPV = QPushButton('Barra PV')
        self.PushButtonPQ = QPushButton('Barra PQ')
        self.ElementSelectorButtonsLayout.addWidget(self.PushButtonTrafo, 1, 1)
        self.ElementSelectorButtonsLayout.addWidget(self.PushButtonLT, 2, 1)
        self.ElementSelectorButtonsLayout.addWidget(self.PushButtonPV, 3, 1)
        self.ElementSelectorButtonsLayout.addWidget(self.PushButtonPQ, 4, 1)

        self.ToggleButtonsContainer = QVBoxLayout()
        self.ToggleButtonsContainer.addStretch()
        self.ToggleButtonsContainer.addLayout(self.ElementSelectorButtonsLayout)
        self.ToggleButtonsContainer.addStretch()

        self.TopLayout = QHBoxLayout()
        self.TopLayout.addLayout(self.ToggleButtonsContainer)
        self.TopLayout.addLayout(self.SchemeInputLayout)

        self.setLayout(self.TopLayout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    scene = SchemeInputer()
    view = QGraphicsView(scene)
    ex = CircuitInputer(view)
    ex.show()
    sys.exit(app.exec_())