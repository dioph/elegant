from elegant.tests import test_core, test_interface, test_methods, test_report
import unittest

tests = [test_core, test_interface, test_methods, test_report]

if __name__ == '__main__':
    for test in tests:
        unittest.main(test, exit=False, verbosity=2)
