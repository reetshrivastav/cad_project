"""Bounded frozen-head Phase 2 transfer test; exact Phase 1 overlap exclusions."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from context_pair_v2 import digest,MODES,load_embedder,pair_features
from llmail_short_model import encode
from llmail_thresholds import at_threshold
from audit_llmail_groups import text_key,label_class
from download_llmail_phase1 import download,REVISION
from prepare_llmail_short_baseline import normalized_text
from check_llmail_readiness import tokens
PHASE2_FILES=('data/labelled_unique_submissions_phase2.json','data/raw_submissions_phase2.jsonl')
# Phase 2 uses levels 1/2 for the two retrieval scenarios (original scenarios 3/4).
SCENARIO_MAP={'1':'scenario_3','2':'scenario_4'}
POLICY=ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json'
VERIFIED=ROOT/'reports/evidence/llmail_short_training_20261023/verified_summary.json'
INTAKE=ROOT/'reports/evidence/llmail_intake_20261023/llmail_phase1_intake_summary.json'


def keys(text):
    return (hashlib.sha256(normalized_text(text).encode()).hexdigest(),
            hashlib.sha256(json.dumps(sorted(tokens(text)),ensure_ascii=False).encode()).hexdigest())


def projected_task(level,scenarios):
    match=re.fullmatch(r'level([12])[k-v]',level)
    if not match:raise ValueError('Unknown Phase 2 level: '+str(level))
    scenario=SCENARIO_MAP[match[1]];task=scenarios[scenario]['user_query']
    if not isinstance(task,str) or not task.strip():raise ValueError('Missing original user query')
    if scenario=='scenario_3' and 'zenith' not in task.casefold():raise ValueError('Scenario 3 query is not Project Zenith; verify source mapping')
    if scenario=='scenario_4' and 'q2' not in task.casefold():raise ValueError('Scenario 4 query is not Q2; verify source mapping')
    return scenario,task


def transfer_cohort(rows,phase1_teams):
    return all(team not in phase1_teams for team in rows) and bool(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True);parser.add_argument('--group-dir',type=Path,required=True)
    parser.add_argument('--models-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a new empty output directory')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    result={'source_revision':REVISION,'script_sha256':digest(__file__),'training_performed':False,
            'protocol':{'inspect_hash_first':5000,'score_maximum':2000,'seed':'phase2-transfer-v1',
                        'phase2_level_to_original_scenario':SCENARIO_MAP,'cutoffs':'Unchanged original and validation-selected policy.',
                        'overlap_policy':'Exclude normalized exact text or exact token-bag match against ALL Phase 1 annotation texts; report team overlap separately.'},
            'files':{},'status':'started','limitations':['Same publisher/challenge across phases, not independent-source or production telemetry.',
                'Automated source annotations, one-email projection, selectively short full emails.',
                'Exact lexical overlap filtering does not rule out near-duplicate/template/pretraining contamination.',
                'Cutoffs and models fixed before Phase 2 inspection. Hash-bounded sample is not the entire Phase 2 corpus.']}
    try:
        verified=json.loads(VERIFIED.read_text());metadata_path=args.models_dir/'baseline_metadata.json'
        if digest(metadata_path)!=verified['metadata_sha256']:raise ValueError('Frozen metadata mismatch')
        metadata=json.loads(metadata_path.read_text());policy=json.loads(POLICY.read_text())
        if policy['metadata_sha256']!=verified['metadata_sha256'] or policy['selector_module_sha256']!=digest(ROOT/'llmail_thresholds.py'):raise ValueError('Frozen cutoff mismatch')
        if metadata['module_sha256']!=digest(ROOT/'llmail_short_model.py') or metadata['feature_module_sha256']!=digest(ROOT/'context_pair_v2.py'):raise ValueError('Feature source mismatch')
        for name,expected in verified['artifact_sha256'].items():
            if digest(args.models_dir/name)!=expected:raise ValueError('Frozen artifact mismatch')
        expected={r['file']:r['sha256'] for r in json.loads(INTAKE.read_text())['files']}
        for name in ('data/labelled_unique_submissions_phase1.json','data/scenarios.json'):
            if digest(args.source_dir/name)!=expected[name]:raise ValueError('Phase 1 input checksum mismatch')
        scenarios=json.loads((args.source_dir/'data/scenarios.json').read_text())
        for level in ('level1k','level2k'):projected_task(level,scenarios)
        group_summary=json.loads((args.group_dir/'group_audit_summary.json').read_text())
        frozen_group=ROOT/'reports/evidence/llmail_groups_corrected_20261023/llmail_group_audit_corrected.json'
        if digest(args.group_dir/'group_audit_summary.json')!=digest(frozen_group):raise ValueError('Phase 1 group audit mismatch')
        connection=sqlite3.connect((args.group_dir/'exact_join_index.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
        phase1_teams={r[0] for r in connection.execute('SELECT team FROM team_components')};connection.close()
        if len(phase1_teams)!=group_summary['teams']:raise ValueError('Team index count mismatch')
        for relative in PHASE2_FILES:
            print('Downloading pinned '+relative+' ...',flush=True)
            result['files'][relative]=download(relative,args.output_dir/relative)
        print('Indexing Phase 1 annotation overlap keys on CPU...',flush=True)
        phase1=json.loads((args.source_dir/'data/labelled_unique_submissions_phase1.json').read_text())
        seen_text=set();seen_bags=set()
        for text in phase1:
            a,b=keys(text);seen_text.add(a);seen_bags.add(b)
        del phase1
        annotations=json.loads((args.output_dir/PHASE2_FILES[0]).read_text())
        if not isinstance(annotations,dict):raise ValueError('Unexpected Phase 2 annotation schema')
        source_labels=Counter();excluded=Counter();candidates={}
        for text,annotation in annotations.items():
            if not isinstance(text,str) or not isinstance(annotation,dict):raise ValueError('Unexpected annotation entry')
            label=label_class(annotation.get('attack_attempt'));source_labels[label]+=1
            if label not in ('True','False'):excluded[label]+=1;continue
            a,b=keys(text)
            if a in seen_text:excluded['phase1_normalized_text_overlap']+=1;continue
            if b in seen_bags:excluded['phase1_token_bag_overlap']+=1;continue
            key=hashlib.sha256(text.encode()).hexdigest();candidates[key]={'text':text,'label':label,'reason':annotation.get('reason')}
        del annotations,seen_text,seen_bags
        owners=defaultdict(set);levels=defaultdict(set);raw_rows=0;missing_team_rows=0
        with (args.output_dir/PHASE2_FILES[1]).open() as handle:
            for line in handle:
                if not line.strip():continue
                raw_rows+=1;row=json.loads(line);text=text_key(row.get('subject'),row.get('body'))
                if text is None:continue
                key=hashlib.sha256(text.encode()).hexdigest()
                if key not in candidates:continue
                level=row.get('scenario');projected_task(level,scenarios)
                team=row.get('team_id')
                if not isinstance(team,str) or not team:missing_team_rows+=1;owners[key].add('__missing_team__')
                else:owners[key].add(team)
                levels[key].add(level)
        matched=[]
        for key,value in candidates.items():
            if key not in owners or '__missing_team__' in owners[key]:excluded['unmatched_or_missing_team']+=1;continue
            scenario,task=projected_task(sorted(levels[key])[0],scenarios)
            matched.append({'id':'LLMAIL-P2-'+key,'task':task,'untrusted_content':value['text'],
                            'source_attack_attempt':value['label'],'source_reason':value['reason'],
                            'observed_scenario':scenario,'team_new':transfer_cohort(owners[key],phase1_teams)})
        result.update(source_annotation_counts=dict(source_labels),raw_phase2_rows=raw_rows,matched_missing_team_raw_rows=missing_team_rows,
                      novel_matched_candidate_count=len(matched),novel_matched_team_new_count=sum(r['team_new'] for r in matched),overlap_and_schema_exclusions=dict(excluded))
        matched.sort(key=lambda r:hashlib.sha256(('phase2-transfer-v1:'+r['id']).encode()).hexdigest())
        sample=matched[:5000];del candidates,matched
        embedder,revision=load_embedder(metadata['embedding_revision'])
        text_lengths=embedder.tokenizer([r['untrusted_content'] for r in sample],truncation=False,add_special_tokens=True)['input_ids'] if sample else []
        task_lengths=embedder.tokenizer([r['task'] for r in sample],truncation=False,add_special_tokens=True)['input_ids'] if sample else []
        eligible=[r for r,a,b in zip(sample,text_lengths,task_lengths) if max(len(a),len(b))<=256]
        selected=eligible[:2000]
        result.update(hash_sample_inspected=len(sample),hash_sample_long_excluded=len(sample)-len(eligible),eligible_short_sample_count=len(eligible),scored_count=len(selected),scored_labels=dict(Counter(r['source_attack_attempt'] for r in selected)),scored_team_new_count=sum(r['team_new'] for r in selected))
        result.update(policy_sha256=digest(POLICY),metadata_sha256=digest(metadata_path),embedding_revision=revision,
                      device=str(embedder.device),dtype=str(next(embedder.parameters()).dtype),models={})
        if selected:
            print(f'Scoring {len(selected)} frozen-model transfer cases...',flush=True)
            task,content=encode(selected,embedder)
            if task.shape[1]!=metadata['embedding_width']:raise ValueError('Embedding width mismatch')
            from xgboost import XGBClassifier
            for mode in MODES:
                model=XGBClassifier();model.load_model(args.models_dir/(mode+'.ubj'));features=pair_features(task,content,mode)
                if model.n_features_in_!=features.shape[1]:raise ValueError('Model width mismatch')
                p=np.asarray(model.predict_proba(features)[:,1],dtype=np.float64)
                cohorts={}
                for name,mask in [('all_text_novel',np.ones(len(selected),dtype=bool)),('text_and_team_new',np.array([r['team_new'] for r in selected]))]:
                    subset=[r for r,keep in zip(selected,mask) if keep]
                    cohorts[name]={'count':len(subset)}
                    if subset:
                        cohorts[name].update(original_cutoff=at_threshold(subset,p[mask],.5),validation_selected_cutoff=at_threshold(subset,p[mask],policy['thresholds'][mode]))
                result['models'][mode]={'cohorts':cohorts,'rows':[{'id':r['id'],'source_attack_attempt':r['source_attack_attempt'],'team_new':r['team_new'],'observed_scenario':r['observed_scenario'],'probability':float(v)} for r,v in zip(selected,p)]}
        result['status']='completed' if selected else 'completed_no_eligible_cases'
    except Exception as error:
        result.update(status='failed',error=f'{type(error).__name__}: {error}')
    result.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),client_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (args.output_dir/'phase2_transfer_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='models'},indent=2))
    if result['status']=='failed':raise SystemExit(1)

if __name__=='__main__':main()
