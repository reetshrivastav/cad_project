"""Frozen-model full-coverage sliding-window test on bounded reserved long emails."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest,MODES,load_embedder,pair_features
from llmail_thresholds import at_threshold
from llmail_long_windows import windows,embed_token_windows,aggregate
PREP=ROOT/'reports/evidence/llmail_preparation_20261023/llmail_preparation_summary.json'
POLICY=ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json'
VERIFIED=ROOT/'reports/evidence/llmail_short_training_20261023/verified_summary.json'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepared-dir',type=Path,required=True);parser.add_argument('--models-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh output directory')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    result={'status':'started','script_sha256':digest(__file__),'window_module_sha256':digest(ROOT/'llmail_long_windows.py'),
            'protocol':{'window_including_specials':256,'overlap_content_tokens':32,'hash_sample_max_emails':300,'window_budget':20000,
                        'sample_seed':'long-email-v1','aggregations':['first_window','max_window','mean_window'],
                        'partial_email_scoring':False,'cutoffs':'Unchanged original and frozen short-validation-selected cutoffs; no long-input tuning.'},
            'training_performed':False,'limitations':['Frozen heads trained on short complete emails; chunks are a changed input distribution.',
                'Only email-level publisher source annotations; chunk labels/location of malicious spans unknown.',
                'Max pooling can amplify false alarms; mean pooling can dilute localized instructions.',
                'Same source, selected long holdout subset; not independent human labels or downstream attack success.',
                'Offline full-token coverage does not establish full-conversation reasoning or live gateway long-email protection.']}
    try:
        summary=json.loads(PREP.read_text());path=args.prepared_dir/'test.jsonl'
        if digest(path)!=summary['files']['test']['sha256']:raise ValueError('Original full-test checksum mismatch')
        verified=json.loads(VERIFIED.read_text());metadata_path=args.models_dir/'baseline_metadata.json'
        if digest(metadata_path)!=verified['metadata_sha256']:raise ValueError('Frozen metadata mismatch')
        metadata=json.loads(metadata_path.read_text());policy=json.loads(POLICY.read_text())
        if policy['metadata_sha256']!=verified['metadata_sha256'] or policy['selector_module_sha256']!=digest(ROOT/'llmail_thresholds.py'):raise ValueError('Frozen cutoff mismatch')
        if metadata['module_sha256']!=digest(ROOT/'llmail_short_model.py') or metadata['feature_module_sha256']!=digest(ROOT/'context_pair_v2.py'):raise ValueError('Feature source mismatch')
        for name,expected in verified['artifact_sha256'].items():
            if digest(args.models_dir/name)!=expected:raise ValueError('Frozen artifact mismatch')
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        if len(rows)!=17536 or any(r['split']!='test' for r in rows):raise ValueError('Full test row count/split mismatch')
        if len({r['id'] for r in rows})!=len(rows) or {r['id'] for r in rows}&set(metadata['training_ids']+metadata['validation_ids']):raise ValueError('Duplicate/development overlap')
        embedder,revision=load_embedder(metadata['embedding_revision'])
        if embedder.max_seq_length!=256:raise ValueError('Unexpected encoder window')
        special=embedder.tokenizer.num_special_tokens_to_add(pair=False);capacity=256-special
        if capacity<=32:raise ValueError('Special tokens leave insufficient window capacity')
        print('Tokenizing full reserved emails without truncation...',flush=True)
        long=[]
        for start in range(0,len(rows),64):
            batch=rows[start:start+64];encoded=embedder.tokenizer([r['untrusted_content'] for r in batch],truncation=False,add_special_tokens=False)['input_ids']
            for row,ids in zip(batch,encoded):
                if len(ids)+special>256:long.append((row,ids))
        counts=dict(Counter(r['source_attack_attempt'] for r,_ in long))
        expected_long=json.loads((ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json').read_text())['excluded_long_counts']['test']
        if counts!=expected_long:raise ValueError('Long cohort differs from recorded tokenizer coverage')
        long.sort(key=lambda item:hashlib.sha256(('long-email-v1:'+item[0]['id']).encode()).hexdigest())
        sample=long[:300];result.update(long_candidate_count=len(long),long_candidate_labels=counts,hash_sample_count=len(sample))
        selected=[];excluded=[];total_windows=0
        for row,ids in sample:
            chunks=windows(ids,capacity,32)
            if total_windows+len(chunks)>20000:
                excluded.append({'id':row['id'],'reason':'whole_email_window_budget','content_tokens':len(ids),'windows_needed':len(chunks)});continue
            selected.append((row,ids,chunks));total_windows+=len(chunks)
        task_texts=sorted({r['task'] for r,_,_ in selected})
        task_lengths=embedder.tokenizer(task_texts,truncation=False,add_special_tokens=True)['input_ids']
        if any(len(ids)>256 for ids in task_lengths):raise ValueError('Trusted task exceeds window; do not truncate')
        task_vectors=embedder.encode(task_texts,convert_to_numpy=True,normalize_embeddings=True,batch_size=32,show_progress_bar=False)
        task_lookup=dict(zip(task_texts,np.asarray(task_vectors,dtype=np.float32)))
        from xgboost import XGBClassifier
        heads={}
        for mode in MODES:
            head=XGBClassifier();head.load_model(args.models_dir/(mode+'.ubj'));heads[mode]=head
        scored={mode:[] for mode in MODES}
        print(f'Scoring {len(selected)} long emails using {total_windows} complete windows...',flush=True)
        for index,(row,ids,chunks) in enumerate(selected,1):
            content=embed_token_windows([chunk for _,_,chunk in chunks],embedder)
            if content.shape[1]!=metadata['embedding_width']:raise ValueError('Embedding width mismatch')
            task=np.repeat(task_lookup[row['task']][None,:],len(chunks),axis=0)
            for mode in MODES:
                features=pair_features(task,content,mode)
                if heads[mode].n_features_in_!=features.shape[1]:raise ValueError('Feature width mismatch')
                p=np.asarray(heads[mode].predict_proba(features)[:,1],dtype=np.float64)
                scored[mode].append({'id':row['id'],'component_sha256':row['component_sha256'],'source_attack_attempt':row['source_attack_attempt'],
                                     'content_tokens':len(ids),'window_intervals':[[a,b] for a,b,_ in chunks],
                                     'window_probabilities':p.tolist(),'aggregated':aggregate(p)})
            if index%25==0:print(f'{index}/{len(selected)} emails complete',flush=True)
        result.update(status='completed',scored_count=len(selected),scored_labels=dict(Counter(r['source_attack_attempt'] for r,_,_ in selected)),
                      total_windows=total_windows,content_tokens_covered=sum(len(ids) for _,ids,_ in selected),
                      fully_covered_emails=len(selected),excluded_whole_emails=excluded,
                      policy_sha256=digest(POLICY),metadata_sha256=digest(metadata_path),source_test_sha256=digest(path),
                      embedding_revision=revision,device=str(embedder.device),dtype=str(next(embedder.parameters()).dtype),models={})
        if not selected:result['status']='completed_no_eligible_cases'
        for mode,observations in scored.items():
            summaries={}
            if observations:
                for aggregation in ('first_window','max_window','mean_window'):
                    probabilities=[r['aggregated'][aggregation] for r in observations]
                    summaries[aggregation]={'original_cutoff':at_threshold(observations,probabilities,.5),
                                             'frozen_short_validation_cutoff':at_threshold(observations,probabilities,policy['thresholds'][mode])}
            result['models'][mode]={'metrics':summaries,'rows':observations}
    except Exception as error:result.update(status='failed',error=f'{type(error).__name__}: {error}')
    result.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),client_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (args.output_dir/'long_email_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='models'},indent=2))
    if result['status']=='failed':raise SystemExit(1)

if __name__=='__main__':main()
