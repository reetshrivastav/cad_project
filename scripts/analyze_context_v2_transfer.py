"""Verify recorded frozen-model wording-transfer evidence without GPU inference."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import MODES,digest,outcome_metrics
from evaluate_context_v2_transfer import CASES,load_cases
from analyze_context_v2 import analyze,PREFIX
ARCHIVE=ROOT/'reports/evidence/context_v2_scoring_20261023/context-v2-lab-results.tar.gz'


def analyze_transfer(path):
    verified=analyze(ARCHIVE)
    with tarfile.open(ARCHIVE) as archive:
        metadata=json.load(archive.extractfile(PREFIX+'context_metadata.json'))
    result=json.loads(Path(path).read_text());rows=load_cases()
    def require(condition,message):
        if not condition:raise ValueError(message)
    require(result['script_sha256']==digest(ROOT/'scripts/evaluate_context_v2_transfer.py'),'Scorer checksum mismatch')
    require(result['module_sha256']==digest(ROOT/'context_pair_v2.py'),'Module checksum mismatch')
    require(result['corpus_sha256']==digest(CASES),'Corpus checksum mismatch')
    require(result['metadata_sha256']==verified['member_sha256'][PREFIX+'context_metadata.json'],'Metadata checksum mismatch')
    require(result['artifact_sha256']==metadata['artifact_sha256'],'Models differ from topic test')
    require(result['embedding_revision']==metadata['embedding_revision'],'Encoder revision mismatch')
    require(result['device']=='cuda:0' and result['dtype']=='torch.float16','GPU record mismatch')
    require(set(result['models'])==set(MODES),'Model modes mismatch')
    summary={}
    for mode in MODES:
        scored=result['models'][mode]['rows']
        require(len(scored)==len(rows),'Missing observations')
        for actual,expected in zip(scored,rows):
            require(all(actual.get(k)==v for k,v in expected.items()),'Input row mismatch')
            require(actual['decision']==('review_redirection' if actual['review_probability']>=.5 else 'allow_task'),'Decision mismatch')
        metrics=outcome_metrics(rows,[r['review_probability'] for r in scored])
        require(metrics==result['models'][mode]['metrics'],'Metrics mismatch')
        summary[mode]=metrics
    pair=result['models']['pair']['rows']
    groups={g:outcome_metrics([r for r in pair if r['group_id']==g],[r['review_probability'] for r in pair if r['group_id']==g]) for g in sorted({r['group_id'] for r in rows})}
    return dict(source_sha256=digest(path),models=summary,pair_by_topic=groups,
                pair_errors=[r for r in pair if r['decision']!=r['label']],
                verification_scope='Recorded hashes, inputs and probabilities/metrics reconciled; GPU inference not reproduced.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=analyze_transfer(args.input)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary['models'],indent=2))

if __name__=='__main__':main()
