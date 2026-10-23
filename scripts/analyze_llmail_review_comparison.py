"""Reconcile AI/source review comparison and rescore saved validation probabilities."""
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
MANIFEST=ROOT/'reports/evidence/llmail_label_review_ai_20261023/review_manifest.json'


def analyze(comparison_path,blind_path):
    result=json.loads(Path(comparison_path).read_text());manifest=json.loads(MANIFEST.read_text())
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(result['script_sha256']==digest(ROOT/'scripts/compare_llmail_label_review.py'),'Comparator mismatch')
    require(result['review_csv_sha256']==manifest['reviewed_csv_sha256'],'Reviewed CSV identity mismatch')
    source=json.loads((ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json').read_text())
    require(result['validation_sha256']==source['files']['validation']['sha256'],'Validation identity mismatch')
    require(digest(blind_path)==manifest['source_csv_sha256'],'Blind input identity mismatch')
    require(not result['training_performed'] and not result['reserved_test_used'],'Scope mismatch')
    reviewed=result['rows'];require(len(reviewed)==80 and len({r['review_id'] for r in reviewed})==80,'Review IDs missing/duplicated')
    expected={r['review_id']:r for r in manifest['rows']}
    for row in reviewed:
        require(row['review_id'] in expected,'Unknown review ID')
        for key,original_key in [('review_label','label'),('reviewer','reviewer'),('notes','notes')]:require(row[key]==expected[row['review_id']][original_key],'AI review changed')
        require(row['source_label'] in ('True','False'),'Unsupported source label')
    require(dict(Counter(r['review_label'] for r in reviewed))==result['review_counts']==manifest['counts'],'Label count mismatch')
    require(dict(Counter(r['source_label']+'/'+r['review_label'] for r in reviewed))==result['source_label_vs_review'],'Cross-tab mismatch')
    require(dict(Counter(r['reviewer'] for r in reviewed))==result['reviewers'],'Reviewer mismatch')
    with Path(blind_path).open(newline='',encoding='utf-8') as handle:blind={r['review_id']:r for r in csv.DictReader(handle)}
    require(set(blind)==set(expected),'Blind IDs differ')
    archive=ROOT/'reports/evidence/llmail_short_training_20261023/llmail-short-training-v1.tar.gz'
    verified=json.loads((archive.parent/'verified_summary.json').read_text())
    require(digest(archive)==verified['archive_sha256'],'Training archive changed')
    with tarfile.open(archive) as handle:training=json.load(handle.extractfile('models/llmail_short_baseline_v1/training_report.json'))
    policy=json.loads((ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json').read_text())
    summaries={}
    for mode,record in training['models'].items():
        observations={r['id']:r for r in record['observations'] if r['split']=='validation'}
        clear=[];probabilities=[];details=[];source_negative_flags=Counter()
        for review in reviewed:
            text=blind[review['review_id']]['untrusted_content']
            identity='LLMAIL-P1-'+hashlib.sha256(text.encode()).hexdigest()
            require(identity in observations,'Reviewed email not in validation observations')
            observation=observations[identity]
            require(observation['source_attack_attempt']==review['source_label'],'Source label join mismatch')
            probability=observation['probability']
            if review['source_label']=='False' and probability>=.5:source_negative_flags[review['review_label']]+=1
            details.append(dict(review_id=review['review_id'],review_label=review['review_label'],source_label=review['source_label'],probability=probability))
            if review['review_label']=='unclear':continue
            clear.append({'source_attack_attempt':'True' if review['review_label']=='injection' else 'False'});probabilities.append(probability)
        metrics={}
        for name,threshold in [('original_cutoff',.5),('validation_selected_cutoff',policy['thresholds'][mode])]:
            values=at_threshold(clear,probabilities,threshold)
            values['scope']='Post-hoc agreement with AI-only labels on 66 clear cases in a selected validation packet. Not human-adjudicated accuracy, independent model validation, or a replacement for reserved-test findings.'
            # Rename source target metrics for this different diagnostic target.
            for key in list(values):
                if key.startswith('source_'):values['ai_review_'+key[len('source_'):]]=values.pop(key)
            metrics[name]=values
        summaries[mode]={'metrics':metrics,'original_source_negative_flags_by_ai_review':dict(source_negative_flags),'reviewed_probabilities':details}
    return {'comparison_sha256':digest(comparison_path),'blind_csv_sha256':digest(blind_path),
            'review_counts':result['review_counts'],'source_label_vs_review':result['source_label_vs_review'],
            'models':summaries,'clear_cases':66,'unclear_cases_excluded_from_rescoring':14,
            'scope':'AI-only diagnostic rescoring of already-seen validation probabilities. No fitting, embeddings, new model selection or held-out scoring.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--comparison',type=Path,required=True);parser.add_argument('--blind-csv',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze(args.comparison,args.blind_csv);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='models'},indent=2))

if __name__=='__main__':main()
