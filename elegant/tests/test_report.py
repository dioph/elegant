import os
import pickle
import unittest

from elegant.report import create_report
from elegant.utils import getTestDbFile, getSessionsDir

file = getTestDbFile()
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
        self.assertTrue(os.path.exists(filename),
                        "the pdf test file was not successfully generated")


if __name__ == '__main__':
    unittest.main()
