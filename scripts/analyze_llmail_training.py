"""Reconcile archived LLMail training outputs without loading model weights."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import MODES,digest
from llmail_short_model import LABELS,PARAMS,metrics
PREFIX='models/llmail_short_baseline_v1/'
NAMES={PREFIX+n for n in ('pair.ubj','task_only.ubj','content_only.ubj','training_report.json','baseline_metadata.json')}


def analyze(path):
    files={}
    with tarfile.open(fileobj=io.BytesIO(Path(path).read_bytes()),mode='r:gz') as archive:
        for member in archive:
            if member.isdir() and member.name.rstrip('/')==PREFIX.rstrip('/'):continue
            if not member.isfile() or member.name not in NAMES or member.name in files or member.size>25_000_000:raise ValueError('Unexpected archive entry')
            files[member.name]=archive.extractfile(member).read()
    if set(files)!=NAMES:raise ValueError('Incomplete archive')
    metadata=json.loads(files[PREFIX+'baseline_metadata.json']);report=json.loads(files[PREFIX+'training_report.json'])
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(metadata['module_sha256']==digest(ROOT/'llmail_short_model.py'),'Model module mismatch')
    require(metadata['feature_module_sha256']==digest(ROOT/'context_pair_v2.py'),'Features mismatch')
    require(metadata['trainer_sha256']==digest(ROOT/'scripts/train_llmail_short_baseline.py'),'Trainer mismatch')
    require(metadata['hyperparameters']==PARAMS and metadata['labels']==LABELS and metadata['threshold']==.5,'Model contract mismatch')
    require(metadata['modes']==list(MODES) and set(report['models'])==set(MODES),'Modes mismatch')
    require(metadata['experiment']=='llmail_short_source_annotation_baseline_v1','Experiment mismatch')
    prep=ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json';source=json.loads(prep.read_text())
    require(metadata['preparation_sha256']==digest(prep) and metadata['data_file_sha256']==source['files'],'Preparation mismatch')
    require(set(metadata['artifact_sha256'])=={'pair.ubj','task_only.ubj','content_only.ubj','training_report.json'},'Artifact manifest mismatch')
    for name,expected in metadata['artifact_sha256'].items():require(hashlib.sha256(files[PREFIX+name]).hexdigest()==expected,'Artifact checksum mismatch')
    require(report['test_inputs_encoded']==0 and report['training_count']==3896 and report['validation_count']==1892,'Recorded scope mismatch')
    require(not set(metadata['training_ids'])&set(metadata['validation_ids']),'Development ID overlap')
    for mode,result in report['models'].items():
        observations=result['observations']
        require(len(observations)==5788,'Observation count mismatch')
        for split,id_key in [('train','training_ids'),('validation','validation_ids')]:
            selected=[r for r in observations if r['split']==split]
            require([r['id'] for r in selected]==metadata[id_key],'Observation IDs mismatch')
            require(dict(Counter(r['source_attack_attempt'] for r in selected))==source['retained_counts'][split],'Class counts mismatch')
            require(metrics(selected,[r['probability'] for r in selected])==result[split],'Metrics mismatch')
            require(metrics(selected,[1.]*len(selected))==report['always_source_positive'][split],'Baseline mismatch')
    return {'archive_sha256':digest(path),'metadata_sha256':hashlib.sha256(files[PREFIX+'baseline_metadata.json']).hexdigest(),
            'artifact_sha256':metadata['artifact_sha256'],
            'models':{m:{s:v for s,v in r.items() if s!='observations'} for m,r in report['models'].items()},
            'always_source_positive':report['always_source_positive'],
            'scope':'Recorded source/artifact hashes, IDs, class counts and metrics reconciled; actual CUDA embeddings/inference not reproduced.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze(args.archive);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({m:r['validation'] for m,r in summary['models'].items()},indent=2))

if __name__=='__main__':main()
