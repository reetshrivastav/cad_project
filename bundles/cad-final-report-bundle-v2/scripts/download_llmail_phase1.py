"""Download pinned LLMail Phase 1 and summarize schemas; no fitting or GPU use."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import Request,urlopen

REVISION='1063bdf01ec8762b812d5e06ee768a06faa5a6f7'
BASE=f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{REVISION}/'
FILES=('README.md','data/scenarios.json','data/system_prompt.json','data/levels_descriptions.json',
       'data/objectives_descriptions.json','data/emails_for_fp_tests.json',
       'data/labelled_unique_submissions_phase1.json','data/raw_submissions_phase1.jsonl')
MAX_FILE_BYTES=2*1024**3


def download(relative,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_name(target.name+'.partial');sha=hashlib.sha256();size=0
    try:
        with urlopen(Request(BASE+relative,headers={'User-Agent':'cad-llmail-phase1-intake/1.0'}),timeout=90) as response,partial.open('wb') as handle:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>MAX_FILE_BYTES:raise ValueError('File exceeds 2 GiB intake limit')
                handle.write(chunk);sha.update(chunk)
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True);raise
    return {'file':relative,'bytes':size,'sha256':sha.hexdigest()}


def summarize(path):
    if path.suffix=='.jsonl':
        count=0;fields=Counter();teams=set();scenarios=Counter();missing_team=0;maximum=0
        with path.open() as handle:
            for line in handle:
                if not line.strip():continue
                row=json.loads(line)
                if not isinstance(row,dict):raise ValueError('Expected JSONL objects')
                count+=1;fields.update(row.keys());scenario=row.get('scenario')
                scenarios[str(scenario)]+=1
                team=row.get('team_id')
                if team:teams.add(str(team))
                else:missing_team+=1
                maximum=max(maximum,len(str(row.get('body','')))+len(str(row.get('subject',''))))
        return {'type':'jsonl','rows':count,'field_occurrences':dict(fields),'unique_teams':len(teams),
                'missing_team':missing_team,'scenarios':dict(scenarios),'max_subject_body_characters':maximum}
    value=json.loads(path.read_text())
    summary={'type':type(value).__name__,'count':len(value) if isinstance(value,(dict,list)) else None}
    if path.name.startswith('labelled_unique'):
        if not isinstance(value,dict):raise ValueError('Expected text-keyed annotation dictionary')
        labels=Counter();reasons=Counter();fields=Counter()
        for row in value.values():
            if not isinstance(row,dict):raise ValueError('Expected annotation objects')
            labels[str(row.get('attack_attempt'))]+=1;reasons[str(row.get('reason'))]+=1;fields.update(row.keys())
        summary.update(attack_attempt_values=dict(labels),annotation_reasons=dict(reasons),annotation_fields=dict(fields))
    elif isinstance(value,dict):
        # Schema only: do not expose payload text, task strings or example outputs.
        summary['value_types']=dict(Counter(type(v).__name__ for v in value.values()))
        summary['nested_field_names']=sorted({str(k) for v in value.values() if isinstance(v,dict) for k in v})
    elif isinstance(value,list):summary['item_types']=dict(Counter(type(v).__name__ for v in value))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();root=args.output_dir
    if root.exists() and any(root.iterdir()):parser.error('Choose a new, empty output directory')
    root.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(root).free<6*1024**3:parser.error('At least 6 GiB free disk space required')
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'source_revision':REVISION,
            'phase2_downloaded':False,'training_performed':False,'files':[],'schemas':{},'errors':{},
            'scope':'External Phase 1 intake/schema audit only. No data splitting, classifier labels or efficacy claims.'}
    try:
        for relative in FILES:
            print('Downloading '+relative+' ...',flush=True)
            target=root/relative;record=download(relative,target);report['files'].append(record)
            if target.suffix in ('.json','.jsonl'):report['schemas'][relative]=summarize(target)
            print(f"Saved {record['bytes']} bytes",flush=True)
    except Exception as error:
        report['errors'][relative]=f'{type(error).__name__}: {error}'
    (root/'intake_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'summary':str(root/'intake_summary.json'),'files_completed':len(report['files']),'errors':report['errors']},indent=2))
    if report['errors']:raise SystemExit(1)

if __name__=='__main__':main()
