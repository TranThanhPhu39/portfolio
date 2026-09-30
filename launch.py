from pathlib import Path
from datetime import datetime
import os
from run_six_steps import run

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    os.chdir(root)
    folder = root / ('report_v5_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    print('DANG CHAY BAN V5:', root)
    run(folder)
    os.startfile(str(folder / 'report.html'))
