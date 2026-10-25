"""Reconcile recorded benign diagnostic probabilities; no inference."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest,MODES
from evaluate_llmail_benign import summarize,VERIFIED,INTAKE


def analyze(path):
    result=json.loads(Path(path).read_text());verified=json.loads(VERIFIED.read_text())
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(result['script_sha256']==digest(ROOT/'scripts/evaluate_llmail_benign.py'),'Scorer mismatch')
    require(result['metadata_sha256']==verified['metadata_sha256'],'Model identity mismatch')
    source={r['file']:r['sha256'] for r in json.loads(INTAKE.read_text())['files']}
    require(result['source_email_sha256']==source['data/emails_for_fp_tests.json'] and result['scenario_source_sha256']==source['data/scenarios.json'],'Source identity mismatch')
    require(result['source_count']==203 and not result['reserved_test_scored'] and not result['training_performed'],'Scope mismatch')
    require(set(result['models'])==set(MODES),'Modes mismatch')
    exclusions=result['excluded_rows'];require(dict(Counter(r['reason'] for r in exclusions))==result['excluded_counts'],'Exclusion counts mismatch')
    identities=None
    for mode,record in result['models'].items():
        rows=record['rows'];current=[(r['id'],r['email_sha256']) for r in rows]
        if identities is None:identities=current
        require(current==identities and len(rows)==result['eligible_count'],'Row identities mismatch')
        require(summarize([r['probability'] for r in rows])==record['metrics'],'Metrics mismatch')
        require(all(r['flagged']==(r['probability']>=.5) for r in rows),'Decision mismatch')
    ids=[i for i,_ in identities]+[r['id'] for r in exclusions]
    require(len(set(ids))==203 and set(ids)=={f'LLMAIL-FP-{i:03}' for i in range(203)},'Source IDs incomplete/duplicated')
    return {'source_sha256':digest(path),'models':{m:r['metrics'] for m,r in result['models'].items()},
            'eligible_count':result['eligible_count'],'excluded_counts':result['excluded_counts'],
            'scope':'Recorded probability metrics, ID coverage and source/model hashes reconciled; original source-text filtering and GPU inference not independently reproduced.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze(args.input);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
