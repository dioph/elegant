import unittest

from elegant.interface import *
from elegant.report import *

file = getTestDbFile()
with open(file, 'br') as file:
    db = pickle.load(file)
    system = db['SYSTEM']
    curves = db['CURVES']
    grid = db['GRID']

SESSIONS_DIR = getSessionsDir()


class ReportTests(unittest.TestCase):
    def test_report_was_created(self):
        filename = os.path.join(SESSIONS_DIR, 'report_test.pdf')
        new_filename = create_report(system, curves, grid, filename)
        self.assertTrue(os.path.exists(new_filename), 'the pdf test file was not successfully generated')
        self.assertEqual(os.path.splitext(filename), os.path.splitext(new_filename))
        if PDF_SUPPORT:
            self.assertEqual(filename, new_filename)
