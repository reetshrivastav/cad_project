"""Run cached Phase 2 retry and bounded long-email evaluation sequentially; package results."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path('results/report_extension_v1'))
    args=parser.parse_args();output=args.output_dir if args.output_dir.is_absolute() else ROOT/args.output_dir
    if output.exists() and any(output.iterdir()):parser.error('Result bundle directory is not empty; preserve it and report the earlier run')
    output.mkdir(parents=True,exist_ok=True)
    jobs=[('phase2',[sys.executable,'scripts/evaluate_llmail_phase2.py','--source-dir','data/external/llmail_phase1_v1',
                    '--group-dir','data/external/llmail_phase1_groups_v2','--models-dir','models/llmail_short_baseline_v1',
                    '--phase2-source-dir','data/external/llmail_phase2_transfer_v1','--output-dir','data/external/llmail_phase2_transfer_v2'],
           ROOT/'data/external/llmail_phase2_transfer_v2/phase2_transfer_result.json'),
          ('long_email',[sys.executable,'scripts/evaluate_llmail_long.py','--prepared-dir','data/external/llmail_phase1_prepared_v1',
                         '--models-dir','models/llmail_short_baseline_v1','--output-dir','data/external/llmail_long_window_v1'],
           ROOT/'data/external/llmail_long_window_v1/long_email_result.json')]
    report={'client_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'scope':'Two sequential frozen-model offline tests, no fitting or native gateway changes. Each job limited to 60 minutes.', 'jobs':{}}
    for name,command,result_path in jobs:
        print('\nStarting '+name+'; progress follows. Other servers must stay stopped.',flush=True)
        start=time.monotonic()
        try:code=subprocess.run(command,cwd=ROOT,timeout=3600).returncode
        except subprocess.TimeoutExpired:code=124
        except OSError as error:
            print(str(error),flush=True);code=127
        entry={'returncode':code,'elapsed_seconds':round(time.monotonic()-start,3),'result_present':result_path.is_file()}
        if result_path.is_file():
            shutil.copyfile(result_path,output/result_path.name);entry['result_file']=result_path.name
        report['jobs'][name]=entry
        print(name+' finished: '+json.dumps(entry),flush=True)
    report['all_jobs_returned_success']=all(r['returncode']==0 and r['result_present'] for r in report['jobs'].values())
    (output/'runner_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    desktop=Path.home()/'Desktop';desktop.mkdir(parents=True,exist_ok=True)
    bundle=desktop/'cad-report-extension-v1.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        for path in sorted(output.glob('*.json')):archive.add(path,arcname='report_extension_v1/'+path.name)
    print('\nUpload this result bundle: '+str(bundle),flush=True)
    if not report['all_jobs_returned_success']:raise SystemExit(1)

if __name__=='__main__':main()
