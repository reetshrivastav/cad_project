"""Export source-labeled task/email projections under a frozen component split."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from audit_llmail_groups import label_class
from download_llmail_phase1 import REVISION
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'reports/evidence/llmail_groups_corrected_20261023/component_split_plan.json'


def make_plan(summary):
    components=summary['component_details']
    if len({c['component_sha256'] for c in components})!=len(components):raise ValueError('Duplicate component')
    ratios={'train':.7,'validation':.15,'test':.15};counts=Counter({s:0 for s in ratios});assignments={}
    total=sum(c['matched_annotations_by_label'].get('True',0)+c['matched_annotations_by_label'].get('False',0) for c in components)
    ordered=sorted(components,key=lambda c:(-(c['matched_annotations_by_label'].get('True',0)+c['matched_annotations_by_label'].get('False',0)),c['component_sha256']))
    for c in ordered:
        split=max(ratios,key=lambda s:(total*ratios[s]-counts[s],s))
        assignments[c['component_sha256']]=split
        counts[split]+=c['matched_annotations_by_label'].get('True',0)+c['matched_annotations_by_label'].get('False',0)
    return {'source_revision':REVISION,'group_summary_sha256':None,'rule':'Descending definite-label component size; assign whole group to greatest remaining 70/15/15 target deficit; hash/name tie breaks.',
            'assignments':assignments,'definite_annotation_counts':dict(counts),'target_ratios':ratios,
            'scope':'Exact-text-connected team groups; no near-duplicate/template independence guarantee. Source annotation prediction, not verified malicious intent.'}


def hash_file(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def project(text,annotation,joined,scenarios,assignments):
    label=label_class(annotation.get('attack_attempt'))
    if label not in ('True','False'):return None
    key=hashlib.sha256(text.encode()).hexdigest()
    if key not in joined:return None
    component,level=joined[key]
    match=re.fullmatch(r'level([1-4])[a-j]',level)
    if not match:raise ValueError('Unknown observed level')
    scenario='scenario_'+match.group(1)
    task=scenarios[scenario]['user_query']
    if not isinstance(task,str) or not task.strip():raise ValueError('Invalid legitimate query')
    return {'id':'LLMAIL-P1-'+key,'split':assignments[component],'component_sha256':component,
            'task':task,'untrusted_content':text,'source_attack_attempt':label,
            'source_reason':annotation.get('reason'),'observed_scenario':scenario,
            'projection':'One annotated email and one observed legitimate scenario query; not complete retrieval context or original agent execution.'}


def run(source,index_dir,output):
    plan=json.loads(PLAN.read_text());summary_path=index_dir/'group_audit_summary.json'
    summary=json.loads(summary_path.read_text())
    if hash_file(summary_path)!=plan['group_summary_sha256']:raise ValueError('Group audit differs from frozen split plan')
    if summary['script_sha256']!=hash_file(ROOT/'scripts/audit_llmail_groups.py'):raise ValueError('Grouping source changed')
    if plan['source_revision']!=summary['source_revision'] or summary['source_revision']!=REVISION:raise ValueError('Source revision mismatch')
    for name,expected in summary['source_hashes'].items():
        if hash_file(source/name)!=expected:raise ValueError('Source payload checksum mismatch')
    intake=json.loads((source/'intake_summary.json').read_text())
    scenario_file=source/'data/scenarios.json'
    expected=next(r['sha256'] for r in intake['files'] if r['file']=='data/scenarios.json')
    if hash_file(scenario_file)!=expected:raise ValueError('Scenario checksum mismatch')
    scenarios=json.loads(scenario_file.read_text())
    connection=sqlite3.connect((index_dir/'exact_join_index.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    # All observed teams for an annotated text must agree on the connected component.
    joined={};group_labels={}
    query='SELECT o.text_sha256,c.component,MIN(o.scenario) FROM observations o JOIN team_components c ON o.team=c.team GROUP BY o.text_sha256,c.component'
    for key,component,level in connection.execute(query):
        group=hashlib.sha256(component.encode()).hexdigest()
        if key in joined:raise ValueError('Text crosses connected components')
        joined[key]=(group,level)
    expected_counts={c['component_sha256']:c['matched_annotations_by_label'] for c in summary['component_details']}
    for group,labels in expected_counts.items():group_labels[group]=Counter()
    for key,label in connection.execute('SELECT text_sha256,source_label FROM annotations'):
        if key in joined:group_labels[joined[key][0]][label]+=1
    if any(dict(group_labels[g])!=expected_counts[g] for g in expected_counts):raise ValueError('Index counts differ from audited components')
    connection.close()
    print('Reading annotations and exporting component-disjoint projections...',flush=True)
    annotations=json.loads((source/'data/labelled_unique_submissions_phase1.json').read_text())
    output.mkdir(parents=True,exist_ok=True);handles={s:(output/(s+'.jsonl')).open('x') for s in ('train','validation','test')}
    counts={s:Counter() for s in handles};reasons={s:Counter() for s in handles};excluded=Counter();maximum=Counter()
    try:
        for text,annotation in annotations.items():
            row=project(text,annotation,joined,scenarios,plan['assignments'])
            if row is None:
                label=label_class(annotation.get('attack_attempt'));excluded[label if label not in ('True','False') else 'unmatched_definite']+=1;continue
            s=row['split'];counts[s][row['source_attack_attempt']]+=1;reasons[s][str(row['source_reason'])]+=1
            maximum[s]=max(maximum[s],len(text));handles[s].write(json.dumps(row)+'\n')
    finally:
        for handle in handles.values():handle.close()
    if {s:sum(v.values()) for s,v in counts.items()}!=plan['definite_annotation_counts']:raise ValueError('Export counts differ from split plan')
    result={'source_revision':REVISION,'split_plan_sha256':hash_file(PLAN),'script_sha256':hash_file(Path(__file__)),
            'counts_by_split_and_source_label':{s:dict(c) for s,c in counts.items()},'annotation_reasons':{s:dict(c) for s,c in reasons.items()},
            'excluded':dict(excluded),'max_email_characters':dict(maximum),
            'files':{s:{'bytes':(output/(s+'.jsonl')).stat().st_size,'sha256':hash_file(output/(s+'.jsonl'))} for s in handles},
            'training_performed':False,'phase2_used':False,'benign_fp_emails_used':False,
            'limitations':['Source automated annotations, not independently reviewed malicious-intent labels.',
                            'One-email projection omits other retrieved emails, tool schemas and conversation state.',
                            'Exact group separation does not establish near-duplicate or template independence.',
                            'No tokenizer truncation or embedding applied. Token-window policy still required.',
                            'Phase 1 test is reserved for fitting decisions; source input schema has been inspected.']}
    (output/'preparation_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dir',type=Path,required=True);parser.add_argument('--group-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh output directory')
    run(args.source_dir,args.group_dir,args.output_dir)

if __name__=='__main__':main()
