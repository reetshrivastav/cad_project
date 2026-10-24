"""Record reviewer-supplied targeted adjudication with explicit input-integrity exclusions."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest
from llmail_thresholds import at_threshold


def validate(original,reviewed):
    expected={r['review_id']:r for r in original}
    if len(expected)!=25 or len(reviewed)!=25 or len({r['review_id'] for r in reviewed})!=25 or {r['review_id'] for r in reviewed}!=set(expected):raise ValueError('Expected exactly 25 matching IDs')
    accepted=[];excluded=[]
    for row in reviewed:
        if row['label'] not in ('benign','injection','unclear') or not row['reviewer'].strip() or not row['notes'].strip():raise ValueError('Incomplete review')
        changed=[k for k in ('task','untrusted_content') if row[k]!=expected[row['review_id']][k]]
        if changed:
            excluded.append({'review_id':row['review_id'],'changed_fields':changed,'reason':'Reviewed input differs from original; do not interpret this as an original-text label.'})
        else:accepted.append(row)
    return accepted,excluded


def analyze(original_path,review_path):
    with Path(original_path).open(newline='',encoding='utf-8-sig') as handle:original=list(csv.DictReader(handle))
    with Path(review_path).open(newline='',encoding='utf-8-sig') as handle:reviewed=list(csv.DictReader(handle))
    manifest=json.loads((ROOT/'reports/evidence/llmail_review_comparison_20261023/adjudication_manifest.json').read_text())
    if digest(original_path)!=manifest['csv_sha256']:raise ValueError('Original packet identity mismatch')
    accepted,excluded=validate(original,reviewed)
    clear=[r for r in accepted if r['label']!='unclear'];models={}
    archive=ROOT/'reports/evidence/llmail_short_training_20261023/llmail-short-training-v1.tar.gz'
    verified=json.loads((archive.parent/'verified_summary.json').read_text())
    if digest(archive)!=verified['archive_sha256']:raise ValueError('Training evidence checksum mismatch')
    with tarfile.open(archive) as handle:training=json.load(handle.extractfile('models/llmail_short_baseline_v1/training_report.json'))
    policy=json.loads((ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json').read_text())
    for mode,record in training['models'].items():
        saved={r['id']:r for r in record['observations'] if r['split']=='validation'}
        p=[];targets=[]
        for row in clear:
            ident='LLMAIL-P1-'+hashlib.sha256(row['untrusted_content'].encode()).hexdigest()
            if ident not in saved:raise ValueError('Clear reviewed email not in saved validation observations')
            p.append(saved[ident]['probability']);targets.append({'source_attack_attempt':'True' if row['label']=='injection' else 'False'})
        models[mode]={}
        for name,cutoff in [('original_cutoff',.5),('frozen_validation_selected_cutoff',policy['thresholds'][mode])]:
            values=at_threshold(targets,p,cutoff)
            values['scope']='Post-hoc agreement with supplied reviewer labels on 19 clear targeted development cases, previously AI-exposed. Not a held-out benchmark, independent adjudication or population false-positive estimate.'
            for key in list(values):
                if key.startswith('source_'):values['review_'+key[len('source_'):]]=values.pop(key)
            models[mode][name]=values
    return {'original_packet_sha256':digest(original_path),'submitted_csv_sha256':digest(review_path),
            'submitted_labels':dict(Counter(r['label'] for r in reviewed)),
            'reviewers_as_supplied':dict(Counter(r['reviewer'] for r in reviewed)),
            'accepted_original_text_rows':len(accepted),'accepted_labels':dict(Counter(r['label'] for r in accepted)),
            'excluded_input_integrity':excluded,'clear_cases_for_diagnostic_rescoring':len(clear),'models':models,
            'rows':[{k:r[k] for k in ('review_id','label','reviewer','notes')} for r in reviewed],
            'scope':'Reviewer-supplied judgments; prior AI exposure and targeted selection prevent an independent blinded-ground-truth claim. No model fit, source-label overwrite, cutoff change or new test scoring.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--original-csv',type=Path,required=True);parser.add_argument('--review-csv',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=analyze(args.original_csv,args.review_csv);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('rows','models')},indent=2))

if __name__=='__main__':main()
