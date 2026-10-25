"""Frozen-head false-alarm diagnostic on publisher benign emails, short inputs only."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest,load_embedder,MODES,pair_features
from llmail_short_model import encode
from prepare_llmail_short_baseline import normalized_text
VERIFIED=ROOT/'reports/evidence/llmail_short_training_20261023/verified_summary.json'
INTAKE=ROOT/'reports/evidence/llmail_intake_20261023/llmail_phase1_intake_summary.json'


def select_rows(emails,task,seen,tokenizer):
    if not isinstance(emails,list) or not all(isinstance(t,str) for t in emails):raise ValueError('Expected publisher email strings')
    task_length=len(tokenizer([task],truncation=False,add_special_tokens=True)['input_ids'][0])
    if task_length>256:raise ValueError('Task exceeds encoder window')
    lengths=tokenizer(emails,truncation=False,add_special_tokens=True)['input_ids']
    selected=[];excluded=Counter();observed=set();exclusion_rows=[]
    for index,(text,ids) in enumerate(zip(emails,lengths)):
        normalized=normalized_text(text);reason=None
        if not text.strip():reason='empty'
        elif normalized in observed:reason='duplicate_in_benign_collection'
        elif normalized in seen:reason='normalized_exact_development_overlap'
        elif len(ids)>256:reason='over_256_tokens'
        observed.add(normalized)
        ident=f'LLMAIL-FP-{index:03}'
        if reason:excluded[reason]+=1;exclusion_rows.append({'id':ident,'reason':reason,'email_sha256':hashlib.sha256(text.encode()).hexdigest()});continue
        selected.append(dict(id=ident,task=task,untrusted_content=text))
    return selected,dict(excluded),exclusion_rows


def summarize(probabilities):
    p=np.asarray(probabilities,dtype=float)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probabilities')
    flags=int((p>=.5).sum())
    return {'count':len(p),'threshold':.5,'flagged_publisher_benign':flags,'allowed_publisher_benign':len(p)-flags,
            'publisher_benign_flag_rate':flags/len(p),
            'scope':'Short eligible, development-disjoint by normalized exact text, publisher-designated benign collection. Not independently human-adjudicated production false-positive rate.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True);parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--models-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output exists; choose a new filename')
    verified=json.loads(VERIFIED.read_text());metadata_path=args.models_dir/'baseline_metadata.json'
    if digest(metadata_path)!=verified['metadata_sha256']:raise ValueError('Model metadata differs from verified lab training')
    metadata=json.loads(metadata_path.read_text())
    for name,expected in verified['artifact_sha256'].items():
        if digest(args.models_dir/name)!=expected:raise ValueError('Model artifact checksum mismatch')
    if metadata['module_sha256']!=digest(ROOT/'llmail_short_model.py') or metadata['feature_module_sha256']!=digest(ROOT/'context_pair_v2.py'):raise ValueError('Feature module checksum mismatch')
    source=json.loads(INTAKE.read_text());expected={r['file']:r['sha256'] for r in source['files']}
    for name in ('data/emails_for_fp_tests.json','data/scenarios.json'):
        if digest(args.source_dir/name)!=expected[name]:raise ValueError('Publisher source checksum mismatch')
    seen=set()
    # Do not open the reserved test file, even for overlap screening in this diagnostic.
    for split in ('train','validation'):
        path=args.data_dir/(split+'.jsonl')
        if digest(path)!=metadata['data_file_sha256'][split]['sha256']:raise ValueError('Development file checksum mismatch')
        with path.open() as handle:
            for line in handle:seen.add(normalized_text(json.loads(line)['untrusted_content']))
    emails=json.loads((args.source_dir/'data/emails_for_fp_tests.json').read_text())
    if len(emails)!=203:raise ValueError('Expected 203 publisher benign emails')
    task=json.loads((args.source_dir/'data/scenarios.json').read_text())['scenario_1']['user_query']
    embedder,revision=load_embedder(metadata['embedding_revision'])
    rows,excluded,exclusion_rows=select_rows(emails,task,seen,embedder.tokenizer)
    if not rows:raise ValueError('No eligible benign cases; cannot report a false-alarm rate')
    task_vectors,content_vectors=encode(rows,embedder)
    if task_vectors.shape[1]!=metadata['embedding_width']:raise ValueError('Embedding width mismatch')
    from xgboost import XGBClassifier
    models={}
    for mode in MODES:
        model=XGBClassifier();model.load_model(args.models_dir/(mode+'.ubj'))
        features=pair_features(task_vectors,content_vectors,mode)
        if model.n_features_in_!=features.shape[1]:raise ValueError('Model feature width mismatch')
        p=model.predict_proba(features)[:,1]
        models[mode]={'metrics':summarize(p),'rows':[{'id':r['id'],'email_sha256':hashlib.sha256(r['untrusted_content'].encode()).hexdigest(),'probability':float(v),'flagged':bool(v>=.5)} for r,v in zip(rows,p)]}
    result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'client_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'script_sha256':digest(__file__),'metadata_sha256':digest(metadata_path),'source_email_sha256':expected['data/emails_for_fp_tests.json'],
            'scenario_source_sha256':expected['data/scenarios.json'],'task':task,'embedding_revision':revision,
            'device':str(embedder.device),'dtype':str(next(embedder.parameters()).dtype),'source_count':203,'eligible_count':len(rows),
            'excluded_counts':excluded,'excluded_rows':exclusion_rows,'models':models,
            'reserved_test_scored':False,'training_performed':False,
            'limitations':['Publisher benign designation, not independent human adjudication.',
                            'Same LLMail source/scenario, one-email projection; not independent-source transfer or downstream ASR.',
                            'Long emails and development exact overlaps excluded; approximate overlap not ruled out.',
                            'Fixed existing models and cutoff; this collection becomes diagnostic data after inspection, not a fresh future test.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({'eligible':len(rows),'excluded':excluded,'models':{m:r['metrics'] for m,r in models.items()},'output':str(args.output)},indent=2))

if __name__=='__main__':main()
