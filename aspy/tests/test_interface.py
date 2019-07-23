import sys

from PyQt5.QtWidgets import QApplication

from aspy.interface import ASPy

app = QApplication(sys.argv)
aspy = ASPy()

def test_buses():
    pass

sys.exit(app.exec_())
