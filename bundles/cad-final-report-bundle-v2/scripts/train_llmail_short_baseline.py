"""Train offline short-email source-label models; never tokenizes or scores test inputs."""
import argparse
from datetime import datetime,timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest,load_embedder,MODES
from llmail_short_model import fit_export,LABELS
from check_llmail_readiness import REVISION
RECORDED=ROOT/'reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh model directory')
    if digest(args.data_dir/'short_baseline_summary.json')!=digest(RECORDED):raise ValueError('Unexpected short-email preparation')
    summary=json.loads(RECORDED.read_text());rows=[]
    # Validate all file digests but never parse, tokenize or encode reserved test rows.
    for split,record in summary['files'].items():
        path=args.data_dir/(split+'.jsonl')
        if path.stat().st_size!=record['bytes'] or digest(path)!=record['sha256']:raise ValueError('Prepared file checksum mismatch')
        if split not in ('train','validation'):continue
        split_rows=[json.loads(line) for line in path.read_text().splitlines()]
        if any(r['split']!=split for r in split_rows):raise ValueError('Invalid split field')
        from collections import Counter
        if dict(Counter(r['source_attack_attempt'] for r in split_rows))!=summary['retained_counts'][split]:raise ValueError('Class counts mismatch')
        rows.extend(split_rows)
    print('Loading pinned MiniLM on CUDA/FP16; development inputs only...',flush=True)
    embedder,revision=load_embedder(REVISION)
    report,metadata=fit_export(args.output_dir,rows,embedder)
    metadata.update(experiment='llmail_short_source_annotation_baseline_v1',timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    labels=LABELS,modes=list(MODES),threshold=.5,embedding_revision=revision,
                    device=str(embedder.device),dtype=str(next(embedder.parameters()).dtype),
                    preparation_sha256=digest(RECORDED),data_file_sha256=summary['files'],
                    module_sha256=digest(ROOT/'llmail_short_model.py'),feature_module_sha256=digest(ROOT/'context_pair_v2.py'),
                    trainer_sha256=digest(__file__),client_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    runtime={'python':platform.python_version(),'packages':{p:version(p) for p in ('torch','sentence-transformers','transformers','scikit-learn','xgboost','numpy')}},
                    limitations=['Short-email selectively cleaned source annotation targets; not human-reviewed security ground truth.',
                                 'Only 248 training and 40 validation source negatives; uncertainty and selection bias substantial.',
                                 'Approximate lexical screening is not proof of semantic/template independence.',
                                 'No long-email support, downstream agent evaluation or production integration.',
                                 'Fixed class-balanced weights/parameters/cutoff; no reserved test inputs encoded.'])
    (args.output_dir/'baseline_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'test_inputs_encoded':0,'models':{m:{s:v for s,v in r.items() if s!='observations'} for m,r in report['models'].items()},
                      'always_source_positive':report['always_source_positive'],'output_dir':str(args.output_dir)},indent=2))

if __name__=='__main__':main()
