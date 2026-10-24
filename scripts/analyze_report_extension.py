"""Verify recorded report-extension results, including full window coverage."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest,MODES
from llmail_long_windows import aggregate,windows
from llmail_thresholds import at_threshold


def same(a,b):
    return set(a)==set(b) and all(math.isclose(v,b[k],rel_tol=0,abs_tol=1e-12) if type(v) is float and type(b[k]) is float else v==b[k] for k,v in a.items())


def analyze(path):
    allowed={f'report_extension_v1/{n}.json' for n in ('long_email_result','phase2_transfer_result','runner_summary')};files={}
    with tarfile.open(path) as archive:
        for member in archive:
            if member.isdir() and member.name.rstrip('/')=='report_extension_v1':continue
            if not member.isfile() or member.name not in allowed or member.name in files or member.size>10_000_000:raise ValueError('Unexpected archive member')
            files[member.name]=archive.extractfile(member).read()
    if set(files)!=allowed:raise ValueError('Incomplete bundle')
    data={Path(k).stem:json.loads(v) for k,v in files.items()};long=data['long_email_result'];phase2=data['phase2_transfer_result'];runner=data['runner_summary']
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(long['status']=='completed' and not long['training_performed'],'Long run scope mismatch')
    require(long['script_sha256']==digest(ROOT/'scripts/evaluate_llmail_long.py') and long['window_module_sha256']==digest(ROOT/'llmail_long_windows.py'),'Long source mismatch')
    policy_path=ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json';policy=json.loads(policy_path.read_text())
    require(long['policy_sha256']==digest(policy_path) and long['metadata_sha256']==policy['metadata_sha256'],'Frozen policy/model mismatch')
    full=json.loads((ROOT/'reports/evidence/llmail_preparation_20261023/llmail_preparation_summary.json').read_text())
    require(long['source_test_sha256']==full['files']['test']['sha256'],'Long input mismatch')
    require(long['embedding_revision']=='1110a243fdf4706b3f48f1d95db1a4f5529b4d41' and long['device']=='cuda:0' and long['dtype']=='torch.float16','Encoder record mismatch')
    require(set(long['models'])==set(MODES),'Modes mismatch')
    require(long['long_candidate_count']==3547 and long['long_candidate_labels']=={'True':3283,'False':264},'Long cohort mismatch')
    require(long['scored_count']==long['hash_sample_count']==long['fully_covered_emails']==300 and not long['excluded_whole_emails'],'Coverage count mismatch')
    require(long['protocol']['overlap_content_tokens']==32 and long['protocol']['window_including_specials']==256 and not long['protocol']['partial_email_scoring'],'Window protocol mismatch')
    reference=None;summary={};longest=0
    for mode,record in long['models'].items():
        rows=record['rows'];identity=[(r['id'],r['component_sha256'],r['source_attack_attempt'],r['content_tokens'],r['window_intervals']) for r in rows]
        if reference is None:reference=identity
        require(identity==reference and len({r['id'] for r in rows})==300,'Window row identities differ')
        require(dict(Counter(r['source_attack_attempt'] for r in rows))==long['scored_labels']=={'True':276,'False':24},'Sample labels mismatch')
        for row in rows:
            expected=[[a,b] for a,b,_ in windows(list(range(row['content_tokens'])),254,32)]
            require(row['window_intervals']==expected,'Window token coverage mismatch')
            require(len(row['window_probabilities'])==len(expected),'Window probabilities missing')
            require(aggregate(row['window_probabilities'])==row['aggregated'],'Aggregation mismatch')
            longest=max(longest,row['content_tokens'])
        require(sum(r['content_tokens'] for r in rows)==long['content_tokens_covered']==130735,'Covered-token sum mismatch')
        require(sum(len(r['window_intervals']) for r in rows)==long['total_windows']==723,'Window count mismatch')
        for aggregation,cutoffs in record['metrics'].items():
            require(aggregation in ('first_window','max_window','mean_window'),'Unknown aggregation')
            probabilities=[r['aggregated'][aggregation] for r in rows]
            require(same(at_threshold(rows,probabilities,.5),cutoffs['original_cutoff']),'Original metrics mismatch')
            require(same(at_threshold(rows,probabilities,policy['thresholds'][mode]),cutoffs['frozen_short_validation_cutoff']),'Frozen metrics mismatch')
        summary[mode]=record['metrics']
    require(runner['jobs']['long_email']['returncode']==0 and runner['jobs']['phase2']['returncode']!=0 and not runner['all_jobs_returned_success'],'Runner status mismatch')
    require(phase2['status']=='failed' and not phase2.get('models') and not phase2['training_performed'],'Phase 2 failure mismatch')
    require(phase2['error']=='ValueError: Unknown Phase 2 level: level3c' and phase2['reused_payloads'],'Unexpected Phase 2 failure')
    cache=json.loads((ROOT/'reports/evidence/llmail_phase2_preflight_20261024/failed_result.json').read_text())
    require(phase2['files']==cache['files'],'Cached payload identity mismatch')
    return {'archive_sha256':digest(path),'long_email':{'scored_count':300,'labels':long['scored_labels'],'windows':723,'content_tokens_covered':130735,
             'maximum_sample_content_tokens':longest,'models':summary,'coverage_verified_from_intervals':True},
            'phase2':{'status':'failed_before_predictions','error':phase2['error'],'payloads_reused':True},
            'scope':'Recorded hashes, interval coverage, aggregation and email-level metrics reconciled; actual token identities/embeddings not independently rerun. Raw metric scope text inherits a short-email helper; the verified experiment is long-email window scoring.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze(args.archive);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='long_email'},indent=2))

if __name__=='__main__':main()
