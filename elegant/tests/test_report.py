from elegant.interface import *
from elegant.report import *

file = getTestDbFile()
with open(file, 'br') as file:
    db = pickle.load(file)
    system = db['SYSTEM']
    curves = db['CURVES']
    grid = db['GRID']

SESSIONS_DIR = getSessionsDir()


def test_report_was_created(tmpdir):
    filename = os.path.join(tmpdir, 'report_test.pdf')
    new_filename = create_report(system, curves, grid, filename)
    assert os.path.exists(new_filename), 'the pdf test file was not successfully generated'
    assert os.path.splitext(filename) == os.path.splitext(new_filename)
    assert len(tmpdir.listdir()) == 1
    if PDF_SUPPORT:
        assert filename == new_filename
