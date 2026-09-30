"""Offline 30-stock integration for checklist 1-6; VN entry point is run_vn100.py."""
import argparse,shutil
from pathlib import Path
from run_us_validation import run

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output)
    if out.exists():raise FileExistsError('Choose a new output folder')
    cache=Path(__file__).parent/'data/us_test_cache'
    if not cache.exists():raise FileNotFoundError('Offline test cache missing')
    shutil.copytree(cache,out/'raw')
    run(out)
