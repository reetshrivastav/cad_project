"""Reconcile reserved test archive and frozen cutoff metrics; no inference."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import MODES,digest
from llmail_thresholds import at_threshold


def analyze(path):
    with tarfile.open(path) as archive:
        members=archive.getmembers()
        if len(members)!=1 or not members[0].isfile() or members[0].name!='llmail_reserved_short_v1.json' or members[0].size>30_000_000:raise ValueError('Unexpected archive member')
        result=json.load(archive.extractfile(members[0]))
    policy_path=ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json';policy=json.loads(policy_path.read_text())
    prep=json.loads((ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json').read_text())
    with tarfile.open(ROOT/'reports/evidence/llmail_short_training_20261023/llmail-short-training-v1.tar.gz') as archive:
        metadata=json.load(archive.extractfile('models/llmail_short_baseline_v1/baseline_metadata.json'))
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(result['script_sha256']==digest(ROOT/'scripts/evaluate_llmail_reserved.py'),'Scorer mismatch')
    require(result['threshold_module_sha256']==digest(ROOT/'llmail_thresholds.py') and result['policy_sha256']==digest(policy_path),'Policy mismatch')
    require(result['metadata_sha256']==policy['metadata_sha256'],'Model identity mismatch')
    require(result['test_file_sha256']==prep['files']['test']['sha256'],'Test data mismatch')
    require(result['embedding_revision']==metadata['embedding_revision'] and result['runtime']==metadata['runtime'],'Runtime/checkpoint mismatch')
    require(result['device']=='cuda:0' and result['dtype']=='torch.float16' and not result['training_performed'],'Recorded execution scope mismatch')
    require(set(result['models'])==set(MODES),'Model modes mismatch')
    def same_metrics(a,b):
        # sklearn/NumPy builds can differ in the last bit of AUC/AP reductions.
        return set(a)==set(b) and all(math.isclose(v,b[k],rel_tol=0,abs_tol=1e-12) if type(v) is float and type(b[k]) is float else v==b[k] for k,v in a.items())
    reference=None;development=set(metadata['training_ids']+metadata['validation_ids'])
    for mode,record in result['models'].items():
        rows=record['rows'];identity=[(r['id'],r['component_sha256'],r['source_attack_attempt']) for r in rows]
        if reference is None:reference=identity
        require(identity==reference,'Model input IDs/labels differ')
        ids=[r['id'] for r in rows]
        require(len(ids)==13989 and len(set(ids))==13989 and not set(ids)&development,'Reserved IDs/count mismatch')
        require(dict(Counter(r['source_attack_attempt'] for r in rows))==prep['retained_counts']['test'],'Class counts mismatch')
        probabilities=[r['probability'] for r in rows]
        require(same_metrics(at_threshold(rows,probabilities,.5),record['original_cutoff']),'Original metrics mismatch')
        require(same_metrics(at_threshold(rows,probabilities,policy['thresholds'][mode]),record['validation_selected_cutoff']),'Adjusted metrics mismatch')
        require(same_metrics(at_threshold(rows,[1.]*len(rows),.5),result['always_source_positive']),'Baseline mismatch')
    return {'archive_sha256':digest(path),'models':{m:{k:v for k,v in r.items() if k!='rows'} for m,r in result['models'].items()},
            'test_components':len({g for _,g,_ in reference}),'always_source_positive':result['always_source_positive'],
            'scope':'Recorded hashes, source-label/ID alignment and all probability-derived cutoff metrics reconciled. Source inputs and CUDA inference not independently reproduced.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze(args.archive);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
