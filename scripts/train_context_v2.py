"""Train separately versioned task/content prototype; never scores test rows."""
import argparse
from datetime import datetime,timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from context_pair_v2 import LABELS,MODES,EMBEDDER_NAME,digest,encode_inputs,load_embedder,pair_features,outcome_metrics
from prepare_context_v2 import load_dataset,validate_dataset

PARAMS=dict(n_estimators=80,max_depth=3,learning_rate=.1,subsample=.9,colsample_bytree=.9,
            objective='binary:logistic',eval_metric='logloss',random_state=42,n_jobs=2)


def training_rows(rows):
    validate_dataset(rows)
    return [r for r in rows if r['split'] in ('train','validation')]


def fit_export(target,audit,rows,embedder,embedding_revision,parameters=None):
    import numpy as np
    from xgboost import XGBClassifier
    target=Path(target)
    if target.exists() and any(target.iterdir()):raise ValueError('Output directory not empty; choose a new model version')
    eligible=training_rows(rows)
    if not any(r['split']=='train' for r in eligible) or not any(r['split']=='validation' for r in eligible):
        raise ValueError('Training and validation rows required')
    task,content=encode_inputs(eligible,embedder)
    train=np.asarray([r['split']=='train' for r in eligible])
    y=np.asarray([LABELS[r['label']] for r in eligible])
    target.mkdir(parents=True,exist_ok=True)
    parameters=parameters or PARAMS
    report={'purpose':'Synthetic grouped development sanity check; no test scoring or deployment efficacy.',
            'threshold':.5,'training_count':int(train.sum()),'validation_count':int((~train).sum()),
            'test_inputs_encoded':0,'models':{}}
    for mode in MODES:
        features=pair_features(task,content,mode)
        model=XGBClassifier(**parameters)
        model.fit(features[train],y[train])
        if list(model.classes_)!=[0,1]:raise ValueError('Unexpected class mapping')
        probabilities=model.predict_proba(features)[:,1]
        model.save_model(target/f'{mode}.ubj')
        observations=[{'id':r['id'],'group_id':r['group_id'],'split':r['split'],'label':r['label'],
                       'review_probability':float(p)} for r,p in zip(eligible,probabilities)]
        report['models'][mode]={
            'training_resubstitution':outcome_metrics([r for r in eligible if r['split']=='train'],probabilities[train]),
            'validation_topic_groups':outcome_metrics([r for r in eligible if r['split']=='validation'],probabilities[~train]),
            'observations':observations}
    (target/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    metadata={'experiment':'context_pair_v2_synthetic_development','corpus_sha256':audit['cases_sha256'],
              'labels':LABELS,'modes':list(MODES),'embedding_name':EMBEDDER_NAME,
              'embedding_revision':embedding_revision,'embedding_width':int(task.shape[1]),
              'feature_recipe':'pair=[task,content,abs(task-content),task*content,dot(task,content)]; no IDs/types/labels/splits',
              'threshold':.5,'hyperparameters':parameters,
              'training_ids':[r['id'] for r in eligible if r['split']=='train'],
              'validation_ids':[r['id'] for r in eligible if r['split']=='validation'],
              'artifact_sha256':{name:digest(target/name) for name in
                                 ('pair.ubj','task_only.ubj','content_only.ubj','training_report.json')},
              'module_sha256':digest(ROOT/'context_pair_v2.py'),
              'trainer_sha256':digest(__file__),
              'limitations':audit['limitations']}
    (target/'context_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return report,metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('output directory not empty; choose a new model version')
    audit,rows=load_dataset()
    print('Loading MiniLM on CUDA/FP16; training/validation only, no test encoding.',flush=True)
    embedder,revision=load_embedder()
    report,metadata=fit_export(args.output_dir,audit,rows,embedder,revision)
    metadata.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    runtime={'python':platform.python_version(),'packages':{n:version(n) for n in
                    ('torch','sentence-transformers','transformers','scikit-learn','xgboost','numpy')}},
                    device=str(embedder.device),dtype=str(next(embedder.parameters()).dtype),
                    client_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (args.output_dir/'context_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'output_dir':str(args.output_dir),'test_inputs_encoded':0,
                     'models':{k:{m:v for m,v in r.items() if m!='observations'} for k,r in report['models'].items()}},indent=2))


if __name__=='__main__':main()
