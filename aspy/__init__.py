name = "aspy"
__version__ = "1.0b1"

try:
    __ASPY_SETUP__
except NameError:
    __ASPY_SETUP__ = False

if not __ASPY_SETUP__:
    from .core import *
