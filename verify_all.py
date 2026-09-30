"""Run all tests and record actual versions + complete test output."""
import io
from pathlib import Path
import platform
import sys
import unittest
import numpy
import pandas
import scipy


if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    versions=f'Python {platform.python_version()}\nNumPy {numpy.__version__}\npandas {pandas.__version__}\nSciPy {scipy.__version__}\n'
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(root/'tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    output=versions+'\n'+stream.getvalue()
    (root/'TEST_RESULTS.txt').write_text(output,encoding='utf-8')
    print(output)
    sys.exit(0 if result.wasSuccessful() else 1)
