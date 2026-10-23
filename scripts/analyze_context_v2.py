"""Reconcile archived lab v2 evidence without loading model weights or running CUDA."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import LABELS,MODES,digest,outcome_metrics
from prepare_context_v2 import load_dataset
from train_context_v2 import PARAMS

PREFIX='models/context_native_v2/'
NAMES={PREFIX+n for n in ('pair.ubj','task_only.ubj','content_only.ubj','training_report.json','context_metadata.json')}|{'results/context_v2_topic_test.json'}


def analyze(path):
    files={}
    with tarfile.open(fileobj=io.BytesIO(Path(path).read_bytes()),mode='r:gz') as archive:
        for member in archive:
            if member.isdir() and member.name.rstrip('/')=='models/context_native_v2':continue
            if not member.isfile() or member.name not in NAMES or member.name in files or member.size>20_000_000:
                raise ValueError('Unexpected archive member')
            files[member.name]=archive.extractfile(member).read()
    if set(files)!=NAMES:raise ValueError('Incomplete archive')
    sha=lambda data:hashlib.sha256(data).hexdigest()
    metadata=json.loads(files[PREFIX+'context_metadata.json'])
    training=json.loads(files[PREFIX+'training_report.json'])
    result=json.loads(files['results/context_v2_topic_test.json'])
    audit,rows=load_dataset()
    def require(condition,message):
        if not condition:raise ValueError(message)
    require(metadata['corpus_sha256']==result['corpus_sha256']==audit['cases_sha256'],'Corpus mismatch')
    require(metadata['module_sha256']==digest(ROOT/'context_pair_v2.py'),'Module mismatch')
    require(metadata['trainer_sha256']==digest(ROOT/'scripts/train_context_v2.py'),'Trainer mismatch')
    require(result['script_sha256']==digest(ROOT/'scripts/evaluate_context_v2.py'),'Evaluator mismatch')
    require(result['metadata_sha256']==sha(files[PREFIX+'context_metadata.json']),'Metadata mismatch')
    require(metadata['experiment']=='context_pair_v2_synthetic_development' and metadata['labels']==LABELS,'Experiment/labels mismatch')
    require(metadata['embedding_name']=='all-MiniLM-L6-v2' and metadata['embedding_width']==384,'Encoder contract mismatch')
    require(metadata['hyperparameters']==PARAMS and metadata['threshold']==.5,'Training contract mismatch')
    require(metadata['modes']==list(MODES) and set(result['models'])==set(MODES),'Modes mismatch')
    require(set(metadata['artifact_sha256'])=={'pair.ubj','task_only.ubj','content_only.ubj','training_report.json'},'Manifest mismatch')
    for name,value in metadata['artifact_sha256'].items():require(sha(files[PREFIX+name])==value,'Artifact checksum mismatch')
    for split,key in [('train','training_ids'),('validation','validation_ids')]:
        require(metadata[key]==[r['id'] for r in rows if r['split']==split],'Split IDs mismatch')
    require(training['test_inputs_encoded']==0 and training['training_count']==280 and training['validation_count']==60,'Training scope mismatch')
    require(result['embedding_revision']==metadata['embedding_revision'] and result['runtime']==metadata['runtime'],'Runtime mismatch')
    require(result['dtype']==metadata['dtype']=='torch.float16' and result['device']==metadata['device']=='cuda:0','GPU record mismatch')
    summary={}
    for mode in MODES:
        observations=training['models'][mode]['observations']
        expected=[r for r in rows if r['split']!='test']
        require(len(observations)==len(expected),'Training observations missing')
        for actual,row in zip(observations,expected):
            require(all(actual[k]==row[k] for k in ('id','group_id','split','label')),'Training row mismatch')
        for split,key in [('train','training_resubstitution'),('validation','validation_topic_groups')]:
            selected=[r for r in observations if r['split']==split]
            require(outcome_metrics(selected,[r['review_probability'] for r in selected])==training['models'][mode][key],'Training metrics mismatch')
        scored=result['models'][mode];test=[r for r in rows if r['split']=='test']
        require(len(scored['rows'])==len(test),'Test observations missing')
        for actual,row in zip(scored['rows'],test):
            require(all(actual.get(k)==v for k,v in row.items()),'Test row mismatch')
            require(actual['decision']==('review_redirection' if actual['review_probability']>=.5 else 'allow_task'),'Decision mismatch')
        metrics=outcome_metrics(test,[r['review_probability'] for r in scored['rows']])
        require(metrics==scored['metrics'],'Test metrics mismatch')
        groups={g:outcome_metrics([r for r in scored['rows'] if r['group_id']==g],[r['review_probability'] for r in scored['rows'] if r['group_id']==g]) for g in sorted({r['group_id'] for r in test})}
        require(groups==scored['by_topic_group'],'Group metrics mismatch')
        summary[mode]=metrics
    return {'archive_sha256':digest(path),'member_sha256':{n:sha(v) for n,v in sorted(files.items())},
            'models':summary,'test_topic_groups':6,'pair_errors':[r for r in result['models']['pair']['rows'] if r['decision']!=r['label']],
            'verification_scope':'Hashes, frozen inputs, splits and reported probabilities/metrics reconciled; GPU inference not reproduced.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze(args.archive)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary['models'],indent=2))

if __name__=='__main__':main()
