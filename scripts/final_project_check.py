"""Record final local CPU regression and frozen-artifact verification; no services required."""
import argparse
from datetime import datetime,timezone
from importlib.metadata import version,PackageNotFoundError
import json
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--model-dir',type=Path);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh output directory')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    packages={}
    for package in ('torch','sentence-transformers','transformers','scikit-learn','xgboost','numpy'):
        try:packages[package]=version(package)
        except PackageNotFoundError:packages[package]='not installed'
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'client_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'python':platform.python_version(),'packages':packages,'checks':{},
            'scope':'CPU software regressions and artifact integrity only. Does not rerun GPU experiments, establish security efficacy or deploy a model.'}
    artifact=[sys.executable,'scripts/verify_native_artifacts.py']
    if args.model_dir:artifact+=['--model-dir',str(args.model_dir)]
    jobs=[('native_artifacts',artifact),('cpu_regressions',[sys.executable,'-m','unittest','discover','-s','tests','-v'])]
    for name,command in jobs:
        print('Running '+name+'...',flush=True)
        try:
            result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=300)
            output=result.stdout;code=result.returncode
        except subprocess.TimeoutExpired as error:
            output=error.stdout or b''
            if isinstance(output,bytes):output=output.decode(errors='replace')
            output+='\nCheck timed out after 300 seconds.\n';code=124
        logfile=name+'.txt';(args.output_dir/logfile).write_text(output)
        report['checks'][name]={'returncode':code,'passed':code==0,'log':logfile}
    report['all_passed']=all(c['passed'] for c in report['checks'].values())
    (args.output_dir/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
