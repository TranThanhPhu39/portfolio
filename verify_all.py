"""Run all tests and save actual results."""
from pathlib import Path
import platform
import subprocess
import sys
import numpy
import pandas
import scipy

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests', '-q'], cwd=root, capture_output=True, text=True)
    versions = f'Python {platform.python_version()}\nNumPy {numpy.__version__}\npandas {pandas.__version__}\nSciPy {scipy.__version__}\n'
    output = versions + '\n' + result.stdout + result.stderr
    (root / 'TEST_RESULTS.txt').write_text(output, encoding='utf-8')
    print(output)
    sys.exit(result.returncode)
