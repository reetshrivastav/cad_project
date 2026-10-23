"""Compare completed blinded development review with source labels; never fit a model."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from export_llmail_label_review import choose,FIELDS,PREP
from context_pair_v2 import digest


def compare(validation,review):
    selected=choose(validation)
    if len(review)!=80 or len({r['review_id'] for r in review})!=80:raise ValueError('Expected 80 unique reviewed IDs')
    expected={f'LLMAIL-REVIEW-{i:03}':row for i,row in enumerate(selected,1)}
    if set(r['review_id'] for r in review)!=set(expected):raise ValueError('Review ID mismatch')
    counts=Counter();cross=Counter();reviewers=Counter();comparisons=[]
    for row in review:
        original=expected[row['review_id']]
        if row['task']!=original['task'] or row['untrusted_content']!=original['untrusted_content']:raise ValueError('Task/email text changed')
        if row['label'] not in ('benign','injection','unclear'):raise ValueError('Invalid/unfilled review label')
        if not row['reviewer'].strip() or not row['notes'].strip():raise ValueError('Reviewer and rationale required')
        counts[row['label']]+=1;cross[original['source_attack_attempt']+'/'+row['label']]+=1;reviewers[row['reviewer']]+=1
        comparisons.append({'review_id':row['review_id'],'source_label':original['source_attack_attempt'],
                            'review_label':row['label'],'reviewer':row['reviewer'],'notes':row['notes']})
    return {'review_counts':dict(counts),'source_label_vs_review':dict(cross),'reviewers':dict(reviewers),
            'rows':comparisons,'training_performed':False,'reserved_test_used':False,
            'scope':'Selected validation diagnostic sample; source/review agreement only. Review provenance is reported as supplied, not independently certified. AI-only review is not human ground truth or a model-accuracy benchmark.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,required=True);parser.add_argument('--review-csv',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a fresh output filename')
    expected=json.loads(PREP.read_text());path=args.data_dir/'validation.jsonl'
    if digest(path)!=expected['files']['validation']['sha256']:raise ValueError('Validation data checksum mismatch')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    with args.review_csv.open(newline='',encoding='utf-8-sig') as handle:
        reader=csv.DictReader(handle)
        if reader.fieldnames!=list(FIELDS):raise ValueError('Review CSV columns changed')
        reviewed=list(reader)
    result=compare(rows,reviewed);result.update(review_csv_sha256=digest(args.review_csv),script_sha256=digest(__file__),validation_sha256=digest(path))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
