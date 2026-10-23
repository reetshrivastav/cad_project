"""Export blinded development-only source-label review; no fitting/test inputs."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest
PREP=ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json'
FIELDS=('review_id','task','untrusted_content','label','reviewer','notes')


def choose(rows):
    if any(r['split']!='validation' for r in rows):raise ValueError('Validation rows only')
    negatives=[r for r in rows if r['source_attack_attempt']=='False']
    positives=[r for r in rows if r['source_attack_attempt']=='True']
    if any(r['source_attack_attempt'] not in ('True','False') for r in rows):raise ValueError('Unsupported source label')
    if len(negatives)!=40 or len(positives)<40:raise ValueError('Expected 40 source negatives and enough positives')
    order=lambda r:hashlib.sha256(('llmail-review-v1:'+r['id']).encode()).hexdigest()
    return sorted(negatives+sorted(positives,key=order)[:40],key=lambda r:hashlib.sha256(('llmail-review-shuffle-v1:'+r['id']).encode()).hexdigest())


def export(rows,output):
    selected=choose(rows);output.mkdir(parents=True,exist_ok=True);mapping=[]
    with (output/'llmail-label-review-blind.csv').open('x',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS);writer.writeheader()
        for i,row in enumerate(selected,1):
            rid=f'LLMAIL-REVIEW-{i:03}'
            writer.writerow(dict(review_id=rid,task=row['task'],untrusted_content=row['untrusted_content'],label='',reviewer='',notes=''))
            mapping.append(dict(review_id=rid,id=row['id'],source_attack_attempt=row['source_attack_attempt'],source_reason=row['source_reason'],component_sha256=row['component_sha256']))
    (output/'review_key.json').write_text(json.dumps(mapping,indent=2)+'\n')
    summary={'selected':len(selected),'source_label_counts':dict(Counter(r['source_attack_attempt'] for r in selected)),
             'csv_sha256':digest(output/'llmail-label-review-blind.csv'),'script_sha256':digest(__file__),
             'source':'Validation only: all 40 source negatives and 40 deterministic hash-selected source positives, blinded shuffled order.',
             'scope':'Diagnostic adjudication sample, not representative prevalence or fresh independent model evaluation. Source labels/key withheld from reviewer; no model probabilities shown.'}
    (output/'review_export_summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh output directory')
    summary=json.loads(PREP.read_text());path=args.data_dir/'validation.jsonl'
    if digest(path)!=summary['files']['validation']['sha256']:raise ValueError('Validation file checksum mismatch')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    print(json.dumps(export(rows,args.output_dir),indent=2))

if __name__=='__main__':main()
