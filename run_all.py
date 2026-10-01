"""Tests, checklist 1-6, then VN run. Writes a new timestamped output folder."""
import argparse,datetime,subprocess,sys
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--return-basis',required=True,choices=['provided','prices']);p.add_argument('--rf-basis',required=True,choices=['annual_effective_percent','monthly_percent']);a=p.parse_args()
    root=Path(__file__).resolve().parent
    out=root/'results'/('local_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    def call(*cmd):subprocess.run([sys.executable,*map(str,cmd)],cwd=root,check=True)
    call('verify_all.py')
    call('run_checklist.py','--output',out/'checklist_1_6')
    call('run_vn100.py','--output',out/'vn100','--return-basis',a.return_basis,'--rf-basis',a.rf_basis)
    print('Completed. VN report:',out/'vn100/report.html')
