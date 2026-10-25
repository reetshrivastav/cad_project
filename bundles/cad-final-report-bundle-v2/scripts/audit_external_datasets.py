"""Metadata-only public dataset audit. Standard library; no payload/model downloads."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.request import Request,urlopen

GITHUB_REPOS=('HumanCompatibleAI/tensor-trust-data','microsoft/llmail-inject-challenge-analysis')
HF_REPO='microsoft/llmail-inject-challenge'
MAX_BYTES=8_000_000


def fetch(url):
    request=Request(url,headers={'User-Agent':'cad-dataset-metadata-audit/1.0'})
    with urlopen(request,timeout=45) as response:
        data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('Metadata exceeds download limit')
    return data


def save(directory,name,data):
    (directory/name).write_bytes(data)
    return {'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def git_revision(repo):
    result=subprocess.run(['git','ls-remote',f'https://github.com/{repo}.git','HEAD'],
                          capture_output=True,text=True,timeout=60,check=True)
    revision=result.stdout.split()[0]
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Invalid Git revision')
    return revision


def audit_hf(directory):
    info=json.loads(fetch(f'https://huggingface.co/api/datasets/{HF_REPO}'))
    revision=info['sha']
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Invalid dataset revision')
    # Pin the second metadata request so the file listing and card match the recorded revision.
    pinned=json.loads(fetch(f'https://huggingface.co/api/datasets/{HF_REPO}/revision/{revision}'))
    if pinned['sha']!=revision:raise ValueError('Dataset revision changed')
    listing=[item['rfilename'] for item in pinned.get('siblings',[])]
    result={'source':f'https://huggingface.co/datasets/{HF_REPO}','revision':revision,
            'card_metadata':pinned.get('cardData'), 'files':listing,
            'provenance':save(directory,'llmail_dataset_metadata.json',json.dumps(pinned,indent=2).encode()),
            'payloads_downloaded':False}
    result['readme']=save(directory,'llmail_dataset_README.md',fetch(f'https://huggingface.co/datasets/{HF_REPO}/raw/{revision}/README.md'))
    return result


def audit_github(repo,directory):
    revision=git_revision(repo);prefix=repo.split('/')[-1]
    result={'source':f'https://github.com/{repo}','revision':revision,'payloads_downloaded':False}
    base=f'https://raw.githubusercontent.com/{repo}/{revision}'
    result['readme']=save(directory,prefix+'_README.md',fetch(base+'/README.md'))
    try:
        tree=json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1'))
        result['tree_truncated']=tree.get('truncated',False)
        result['files']=[item['path'] for item in tree['tree'] if item['type']=='blob']
        result['tree_record']=save(directory,prefix+'_tree.json',json.dumps(tree,indent=2).encode())
        license_paths=[p for p in result['files'] if '/' not in p and p.lower().startswith(('license','copying'))]
    except Exception as error:
        result['listing_error']=f'{type(error).__name__}: {error}'
        license_paths=['LICENSE','LICENSE.md','LICENSE.txt']
    result['license_files']=[]
    for path in license_paths:
        try:result['license_files'].append(save(directory,prefix+'_'+path,fetch(base+'/'+path)))
        except HTTPError as error:
            if error.code!=404:raise
    result['license_status']='Documents collected; dataset-specific reuse terms still require review' if result['license_files'] else 'No root license collected; do not infer reuse permission'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Output directory is not empty; choose a fresh directory')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'scope':'Metadata and documentation only; no dataset payloads, model training or GPU work.',
            'sources':{},'errors':{},'next_step':'Review provenance, schemas and data-specific licenses before payload ingestion and grouped split design.'}
    jobs=[('llmail_huggingface',lambda:audit_hf(args.output_dir))]+[(repo,lambda repo=repo:audit_github(repo,args.output_dir)) for repo in GITHUB_REPOS]
    for name,job in jobs:
        print('Auditing '+name+' ...',flush=True)
        try:report['sources'][name]=job()
        except Exception as error:report['errors'][name]=f'{type(error).__name__}: {error}'
    (args.output_dir/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(args.output_dir/'audit.json'),'sources_completed':list(report['sources']),'errors':report['errors']},indent=2))
    # Preserve partial evidence for review, but do not report success when required sources failed.
    if report['errors']:raise SystemExit(1)

if __name__=='__main__':main()
