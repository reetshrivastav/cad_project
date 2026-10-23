"""Score the frozen synthetic topic-test split after separate v2 training."""
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
from context_pair_v2 import MODES,LABELS,digest,encode_inputs,load_embedder,pair_features,outcome_metrics
from prepare_context_v2 import load_dataset


def verify_metadata(model_dir,audit):
    metadata=json.loads((model_dir/'context_metadata.json').read_text())
    if metadata['experiment']!='context_pair_v2_synthetic_development' or metadata['corpus_sha256']!=audit['cases_sha256']:
        raise ValueError('Experiment/corpus identity mismatch')
    if metadata['module_sha256']!=digest(ROOT/'context_pair_v2.py') or metadata['labels']!=LABELS or metadata['threshold']!=.5:
        raise ValueError('Feature recipe/labels/threshold differ from training')
    if metadata['modes']!=list(MODES):raise ValueError('Unexpected model modes')
    if set(metadata['artifact_sha256'])!={'pair.ubj','task_only.ubj','content_only.ubj','training_report.json'}:
        raise ValueError('Missing or unexpected artifact manifest entries')
    for name,expected in metadata['artifact_sha256'].items():
        if Path(name).name!=name or digest(model_dir/name)!=expected:raise ValueError('Artifact checksum mismatch')
    return metadata


def evaluate(model_dir,audit,rows,embedder):
    from xgboost import XGBClassifier
    model_dir=Path(model_dir);metadata=verify_metadata(model_dir,audit)
    test=[r for r in rows if r['split']=='test']
    if set(r['id'] for r in test)&set(metadata['training_ids']+metadata['validation_ids']):
        raise ValueError('Test IDs overlap fitting/development IDs')
    if len(test)!=audit['counts_by_split']['test']:raise ValueError('Missing test cases')
    task,content=encode_inputs(test,embedder)
    if task.shape[1]!=metadata['embedding_width']:raise ValueError('Embedding width differs from training')
    models={}
    for mode in MODES:
        model=XGBClassifier();model.load_model(model_dir/f'{mode}.ubj')
        features=pair_features(task,content,mode)
        if model.n_features_in_!=features.shape[1]:raise ValueError('Model feature dimensions differ')
        probabilities=model.predict_proba(features)[:,1]
        models[mode]={'metrics':outcome_metrics(test,probabilities),
                      'by_topic_group':{group:outcome_metrics([r for r in test if r['group_id']==group],
                                        [p for r,p in zip(test,probabilities) if r['group_id']==group])
                                        for group in sorted({r['group_id'] for r in test})},
                      'rows':[dict(row,review_probability=float(p),decision='review_redirection' if p>=.5 else 'allow_task')
                              for row,p in zip(test,probabilities)]}
    return {'purpose':'Synthetic topic-held-out sanity test; shared authoring templates; not independent security validation.',
            'corpus_sha256':audit['cases_sha256'],'metadata_sha256':digest(model_dir/'context_metadata.json'),
            'model_directory':str(model_dir),'models':models,'limitations':audit['limitations']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output exists; choose a new filename')
    audit,rows=load_dataset();metadata=verify_metadata(args.models_dir,audit)
    print('Loading recorded MiniLM checkpoint; scoring only the 60 topic-test cases.',flush=True)
    embedder,revision=load_embedder(metadata['embedding_revision'])
    result=evaluate(args.models_dir,audit,rows,embedder)
    result.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  client_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  script_sha256=digest(__file__),embedding_revision=revision,
                  device=str(embedder.device),dtype=str(next(embedder.parameters()).dtype),
                  runtime={'python':platform.python_version(),'packages':{n:version(n) for n in
                            ('torch','sentence-transformers','transformers','scikit-learn','xgboost','numpy')}})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({'models':{k:v['metrics'] for k,v in result['models'].items()},'output':str(args.output)},indent=2))


if __name__=='__main__':main()
