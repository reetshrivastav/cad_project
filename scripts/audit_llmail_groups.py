"""Exact Phase 1 annotation/raw join and team-component audit; no model fitting."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from download_llmail_phase1 import REVISION


def text_key(subject,body):
    # Published dataset card's serialization. No stripping, fuzzy repair or label inference.
    if not isinstance(subject,str) or not isinstance(body,str):return None
    return f'Subject of the email: {subject}.   Body: {body}'


def label_class(value):
    if type(value) is str and value in ('True','False','Unclear'):return value
    return 'malformed'


class Components:
    def __init__(self):self.parent={}
    def find(self,x):
        self.parent.setdefault(x,x)
        if self.parent[x]!=x:self.parent[x]=self.find(self.parent[x])
        return self.parent[x]
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parent[max(a,b)]=min(a,b)


def run(root,output):
    intake=json.loads((root/'intake_summary.json').read_text())
    if intake['source_revision']!=REVISION or intake['errors']:raise ValueError('Incomplete/wrong source intake')
    expected={r['file']:r for r in intake['files']}
    for name in ('data/labelled_unique_submissions_phase1.json','data/raw_submissions_phase1.jsonl'):
        h=hashlib.sha256();size=0
        with (root/name).open('rb') as handle:
            for chunk in iter(lambda:handle.read(4*1024*1024),b''):h.update(chunk);size+=len(chunk)
        if h.hexdigest()!=expected[name]['sha256'] or size!=expected[name]['bytes']:raise ValueError('Local source hash mismatch')
    output.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(output/'exact_join_index.sqlite')
    connection.execute('CREATE TABLE annotations (text_sha256 TEXT PRIMARY KEY, source_label TEXT, reason TEXT, characters INTEGER)')
    connection.execute('CREATE TABLE observations (text_sha256 TEXT, team TEXT, scenario TEXT, raw_line INTEGER)')
    print('Loading source annotations (448 MB JSON; allow several GB of host RAM)...',flush=True)
    annotations=json.loads((root/'data/labelled_unique_submissions_phase1.json').read_text())
    labels=Counter();lookup=set()
    for text,record in annotations.items():
        key=hashlib.sha256(text.encode()).hexdigest();label=label_class(record.get('attack_attempt'))
        labels[label]+=1;lookup.add(key)
        connection.execute('INSERT INTO annotations VALUES (?,?,?,?)',(key,label,str(record.get('reason')),len(text)))
    del annotations
    connection.commit()
    matched=0;total=0;missing_team=0;invalid_fields=0;unknown_scenarios=0
    components=Components();owner={};teams=set();batch=[]
    print('Streaming raw submissions; checking exact serialization matches...',flush=True)
    with (root/'data/raw_submissions_phase1.jsonl').open() as handle:
        for line_number,line in enumerate(handle,1):
            if not line.strip():continue
            row=json.loads(line);total+=1
            team=row.get('team_id');scenario=row.get('scenario')
            if not isinstance(team,str) or not team:missing_team+=1;continue
            teams.add(team);components.find(team)
            if not isinstance(scenario,str) or not re.fullmatch(r'level[1-4][a-j]',scenario):unknown_scenarios+=1
            text=text_key(row.get('subject'),row.get('body'))
            if text is None:invalid_fields+=1;continue
            key=hashlib.sha256(text.encode()).hexdigest()
            # Connect shared exact text across ALL raw submissions, including unannotated ones.
            if key in owner:components.union(team,owner[key])
            else:owner[key]=team
            if key in lookup:
                matched+=1;batch.append((key,team,str(scenario),line_number))
                if len(batch)>=10000:
                    connection.executemany('INSERT INTO observations VALUES (?,?,?,?)',batch);batch=[]
    connection.executemany('INSERT INTO observations VALUES (?,?,?,?)',batch)
    connection.execute('CREATE INDEX observed_text ON observations(text_sha256)');connection.commit()
    component_sizes=Counter(components.find(team) for team in teams)
    joined_by_label=dict(connection.execute('SELECT a.source_label,COUNT(DISTINCT a.text_sha256) FROM annotations a JOIN observations o USING(text_sha256) GROUP BY a.source_label'))
    matched_unique=sum(joined_by_label.values())
    connection.close()
    summary={'source_revision':REVISION,'annotation_count':len(lookup),'source_label_counts':dict(labels),
             'raw_rows':total,'matched_raw_rows':matched,'matched_unique_annotations':matched_unique,
             'unmatched_annotations':len(lookup)-matched_unique,'matched_annotations_by_label':joined_by_label,
             'teams':len(teams),'team_components':len(component_sizes),'component_team_sizes_descending':sorted(component_sizes.values(),reverse=True),
             'missing_team_rows':missing_team,'invalid_text_field_rows':invalid_fields,'unknown_scenario_rows':unknown_scenarios,
             'source_hashes':{k:expected[k]['sha256'] for k in ('data/labelled_unique_submissions_phase1.json','data/raw_submissions_phase1.jsonl')},
             'join_recipe':'Exact SHA256 of published Subject of the email serialization; no normalization/fuzzy repair.',
             'split_created':False,'training_performed':False,'phase2_used':False,
             'limitations':['Exact matching only; near-duplicate/template leakage is not resolved.',
                            'Team components are diagnostic, not proof of independent authoring.',
                            'False/Unclear/malformed source annotations have not been converted to benign ground truth.',
                            'No task/context adapter, token-length policy or held-out evaluation has been applied.']}
    (output/'group_audit_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a new empty output directory')
    run(args.source_dir,args.output_dir)

if __name__=='__main__':main()
