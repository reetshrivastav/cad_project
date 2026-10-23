"""One reserved short-email test, frozen heads and original/validation-selected cutoffs."""
import argparse
from collections import Counter
from datetime import datetime,timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import MODES,digest,load_embedder,pair_features
from llmail_short_model import encode
from llmail_thresholds import at_threshold
POLICY=ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json'
VERIFIED=ROOT/'reports/evidence/llmail_short_training_20261023/verified_summary.json'
PREP=ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json'


def test_rows(path,metadata,summary):
    if digest(path)!=summary['files']['test']['sha256']:raise ValueError('Reserved file checksum mismatch')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    if any(r['split']!='test' for r in rows):raise ValueError('Unexpected split field')
    ids=[r['id'] for r in rows]
    if len(ids)!=len(set(ids)) or set(ids)&set(metadata['training_ids']+metadata['validation_ids']):raise ValueError('Duplicate/development test IDs')
    if dict(Counter(r['source_attack_attempt'] for r in rows))!=summary['retained_counts']['test']:raise ValueError('Reserved class counts mismatch')
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,required=True);parser.add_argument('--models-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output exists; do not overwrite reserved evidence')
    policy=json.loads(POLICY.read_text());verified=json.loads(VERIFIED.read_text());summary=json.loads(PREP.read_text())
    metadata_path=args.models_dir/'baseline_metadata.json'
    if digest(metadata_path)!=policy['metadata_sha256'] or digest(metadata_path)!=verified['metadata_sha256']:raise ValueError('Frozen metadata mismatch')
    metadata=json.loads(metadata_path.read_text())
    if policy['selector_module_sha256']!=digest(ROOT/'llmail_thresholds.py'):raise ValueError('Cutoff module mismatch')
    if metadata['module_sha256']!=digest(ROOT/'llmail_short_model.py') or metadata['feature_module_sha256']!=digest(ROOT/'context_pair_v2.py'):raise ValueError('Feature module mismatch')
    for name,expected in verified['artifact_sha256'].items():
        if digest(args.models_dir/name)!=expected:raise ValueError('Frozen artifact mismatch')
    if digest(args.data_dir/'short_baseline_summary.json')!=digest(PREP):raise ValueError('Preparation mismatch')
    rows=test_rows(args.data_dir/'test.jsonl',metadata,summary)
    print(f'Encoding {len(rows)} reserved short emails once; no fitting or cutoff selection...',flush=True)
    embedder,revision=load_embedder(metadata['embedding_revision']);task,content=encode(rows,embedder)
    if task.shape[1]!=metadata['embedding_width']:raise ValueError('Embedding width mismatch')
    from xgboost import XGBClassifier
    models={}
    for mode in MODES:
        model=XGBClassifier();model.load_model(args.models_dir/(mode+'.ubj'))
        features=pair_features(task,content,mode)
        if model.n_features_in_!=features.shape[1]:raise ValueError('Model feature width mismatch')
        p=np.asarray(model.predict_proba(features)[:,1],dtype=np.float64)
        models[mode]={'original_cutoff':at_threshold(rows,p,.5),'validation_selected_cutoff':at_threshold(rows,p,policy['thresholds'][mode]),
                      'rows':[dict(id=r['id'],component_sha256=r['component_sha256'],source_attack_attempt=r['source_attack_attempt'],probability=float(v)) for r,v in zip(rows,p)]}
    result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'client_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'script_sha256':digest(__file__),'threshold_module_sha256':digest(ROOT/'llmail_thresholds.py'),'policy_sha256':digest(POLICY),
            'metadata_sha256':digest(metadata_path),'test_file_sha256':digest(args.data_dir/'test.jsonl'),
            'embedding_revision':revision,'device':str(embedder.device),'dtype':str(next(embedder.parameters()).dtype),
            'runtime':{'python':platform.python_version(),'packages':{p:version(p) for p in ('torch','sentence-transformers','transformers','scikit-learn','xgboost','numpy')}},
            'models':models,'always_source_positive':at_threshold(rows,np.ones(len(rows)),.5),'training_performed':False,
            'limitations':['Reserved from head fitting and numerical cutoff selection; previously involved in dataset QA and priority cleanup.',
                            'Selected short-only source-annotation targets, not independent human-reviewed security ground truth.',
                            'Approximate lexical cleanup does not guarantee semantic/template independence.',
                            'Report both cutoff policies; no subsequent tuning can make this same test fresh again.',
                            'No long-email, separate-source, production integration or downstream attack-success evidence.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({'models':{m:{k:v for k,v in r.items() if k!='rows'} for m,r in models.items()},'output':str(args.output)},indent=2))

if __name__=='__main__':main()
