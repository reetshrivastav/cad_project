"""Paired guard/tag diagnostic using the already-cached pinned candidate."""
import argparse
from datetime import datetime,timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_wrapper_diagnostic import FOLDER,build
from evaluate_injection_candidate import run_cases,file_sha256,THRESHOLDS


def load_cases():
    path=FOLDER/'cases.jsonl'
    audit=json.loads((FOLDER/'audit.json').read_text())
    if file_sha256(path)!=audit['cases_sha256']:raise ValueError('Frozen wrapper cases checksum mismatch')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    _,expected=build()
    if rows!=expected:raise ValueError('Frozen cases differ from declared factorial recipe')
    return audit,rows


def summarize(rows,threshold):
    result={}
    for wrapper in ('G1T1','G1T0','G0T1','G0T0'):
        result[wrapper]={}
        for group in ('clean','benign_added','attack'):
            offered=[r for r in rows if r['wrapper']==wrapper and r['group']==group]
            scored=[r for r in offered if 'error' not in r]
            flagged=sum(r['injection_probability']>threshold for r in scored)
            result[wrapper][group]={'offered':len(offered),'scored':len(scored),
                                  'errors':len(offered)-len(scored),'flagged':flagged,
                                  'flagged_fraction_of_scored':flagged/len(scored) if scored else None}
    return {'threshold':threshold,'rule':'injection_probability > threshold','cells':result}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output exists; choose a new filename')
    audit,cases=load_cases()
    from pinned_injection_runtime import load_detector
    score,metadata=load_detector(local_files_only=True)
    reference_path=ROOT/'reports/evidence/injection_candidate_scoring_20261023/injection_candidate_shadow_v1.json'
    reference=json.loads(reference_path.read_text())
    if metadata['weights_sha256']!=reference['weights_sha256']:raise ValueError('Cached weights differ from previous diagnostic')
    rows=run_cases(cases,score)
    result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'client_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'script_sha256':file_sha256(__file__),'runtime_script_sha256':file_sha256(ROOT/'scripts/pinned_injection_runtime.py'),
            'cases_sha256':audit['cases_sha256'],'previous_result_sha256':file_sha256(reference_path),
            'model':metadata,'comparisons':[summarize(rows,t) for t in THRESHOLDS],
            'runtime':{'python':platform.python_version(),'packages':{n:version(n) for n in
                        ('torch','transformers','huggingface-hub','safetensors')}},
            'total_errors':sum('error' in r for r in rows),'rows':rows,'limitations':audit['limitations']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({'primary_threshold':result['comparisons'][0],'total_errors':result['total_errors']},indent=2))
    print(f'Output: {args.output}')
    if result['total_errors']:raise SystemExit(1)


if __name__=='__main__':main()
