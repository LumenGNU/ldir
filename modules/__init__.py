import sys


__version__ = "1.0.1"


if sys.version_info < (3, 8):
    sys.exit("Требуется Python 3.8 или выше.")
