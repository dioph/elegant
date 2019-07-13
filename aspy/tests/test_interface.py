<<<<<<< Updated upstream
from aspy.SchemeInput import Aspy
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
aspy = Aspy()

def test_buses():
    pass

sys.exit(app.exec_())



=======
import sys, time
import unittest
from unittest import TestCase
import autoit
from PyQt5.QtWidgets import QApplication

from aspy.SchemeInput import Aspy, createLocalData
from aspy.interface_automation import *


class test_element_insertion(TestCase):
    def test_buses_insertion(self):
        pass

if __name__ == '__main__':
    unittest.main(exit=False)
>>>>>>> Stashed changes

