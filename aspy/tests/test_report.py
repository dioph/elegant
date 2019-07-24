from aspy.interface import *
from aspy.report import *
import unittest
import sys, os

if sys.platform in ('win32', 'win64'):
    file = os.path.join(PACKAGEDIR, './data/wtestdb')
elif sys.platform in ('linux'):
    file = os.path.join(PACKAGEDIR, './data/ltestdb')
else:
    file = '.'
with open(file, 'br') as file:
    db = pickle.load(file)
    system = db['SYSTEM']
    curves = db['CURVES']
    grid = db['GRID']

SESSIONS_DIR = getSessionsDir()


class ReportTests(unittest.TestCase):
    def test_report(self):
        filename = os.path.join(SESSIONS_DIR, 'report_test.pdf')
        create_report(system, curves, grid, filename)
        self.assertTrue(os.path.exists(filename), 'the pdf test file was not successfully generated')
