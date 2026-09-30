"""Run actual backtest tests, save output, return nonzero on failure."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    files=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'tests').glob('test_*.py') if p.name not in ('test_factors.py','test_data.py'))
    result=subprocess.run([sys.executable,'-m','pytest',*files,'-q'],cwd=ROOT,capture_output=True,text=True)
    text=result.stdout+result.stderr
    (ROOT/'BACKTEST_TEST_RESULTS.txt').write_text(text,encoding='utf-8');print(text)
    sys.exit(result.returncode)
