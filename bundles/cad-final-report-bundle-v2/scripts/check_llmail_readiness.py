"""CPU token-length and bounded lexical-leakage screen; no fitting or scoring."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import unicodedata
from prepare_llmail_phase1 import hash_file
ROOT=Path(__file__).resolve().parents[1]
RECORDED=ROOT/'reports/evidence/llmail_preparation_20261023/llmail_preparation_summary.json'
REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'


def tokens(text):
    return set(re.findall(r'\w+',unicodedata.normalize('NFKC',text).casefold()))


def anchors(words):
    return sorted(hashlib.blake2b(w.encode(),digest_size=8).hexdigest() for w in words)[:8]


def jaccard(a,b):
    return len(a&b)/len(a|b) if a or b else 1.0


def screen(connection,records,bucket_cap=200,pair_cap=2_000_000):
    connection.execute('CREATE TABLE docs (id TEXT PRIMARY KEY, split TEXT, words TEXT, normalized_sha TEXT)')
    connection.execute('CREATE TABLE anchors (anchor TEXT, id TEXT, split TEXT)')
    connection.execute('CREATE INDEX anchor_lookup ON anchors(anchor)')
    comparisons=0;skipped=0;near=Counter();exact=Counter();exhausted=False;cross_ids=set();doc_count=0
    for row in records:
        doc_count+=1;words=tokens(row['untrusted_content']);aa=anchors(words)
        # Exact normalized-token bag identity, explicitly distinct from exact original text.
        serialized=json.dumps(sorted(words),ensure_ascii=False)
        normalized=hashlib.sha256(serialized.encode()).hexdigest()
        candidates=set()
        for anchor in aa:
            hits=connection.execute('SELECT id FROM anchors WHERE anchor=? AND split!=? LIMIT ?',
                                    (anchor,row['split'],bucket_cap+1)).fetchall()
            if len(hits)>bucket_cap:skipped+=1;continue
            candidates.update(r[0] for r in hits)
        if not exhausted:
            for other_id in sorted(candidates):
                if comparisons>=pair_cap:exhausted=True;break
                other=connection.execute('SELECT split,words,normalized_sha FROM docs WHERE id=?',(other_id,)).fetchone()
                comparisons+=1;pair='/'.join(sorted((row['split'],other[0])))
                if jaccard(words,set(json.loads(other[1])))>=.8:
                    near[pair]+=1;cross_ids.update((row['id'],other_id))
                    if other[2]==normalized:exact[pair]+=1
        connection.execute('INSERT INTO docs VALUES (?,?,?,?)',(row['id'],row['split'],serialized,normalized))
        connection.executemany('INSERT INTO anchors VALUES (?,?,?)',[(a,row['id'],row['split']) for a in aa])
        if doc_count%5000==0:connection.commit();print(f'Lexical screen: {doc_count} rows, {comparisons} pair comparisons',flush=True)
    connection.commit()
    return {'documents':doc_count,'candidate_pairs_compared':comparisons,'pairs_jaccard_ge_0_8':dict(near),
            'candidate_pairs_with_identical_normalized_token_bags':dict(exact),'rows_in_detected_pairs':len(cross_ids),
            'skipped_overfull_anchor_queries':skipped,'pair_budget_exhausted':exhausted,
            'scope':'Approximate screening: eight lowest stable unigram hashes; capped buckets/comparisons. Token bags ignore ordering and negation. No guarantee of detecting all near duplicates or semantic/template leakage.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepared-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh output directory')
    prepared=args.prepared_dir;recorded=json.loads(RECORDED.read_text());local=prepared/'preparation_summary.json'
    if hash_file(local)!=hash_file(RECORDED):raise ValueError('Preparation summary differs from retained evidence')
    for split,record in recorded['files'].items():
        path=prepared/(split+'.jsonl')
        if path.stat().st_size!=record['bytes'] or hash_file(path)!=record['sha256']:raise ValueError('Prepared file checksum mismatch')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2',revision=REVISION,local_files_only=True)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    length_counts=defaultdict(Counter);maximum=Counter();row_counts=Counter()
    def rows():
        for split in ('train','validation','test'):
            with (prepared/(split+'.jsonl')).open() as handle:
                for line in handle:
                    row=json.loads(line)
                    if row['split']!=split:raise ValueError('Split field differs from file')
                    yield row
    batch=[]
    def count_lengths(batch):
        for field in ('task','untrusted_content'):
            encoded=tokenizer([r[field] for r in batch],truncation=False,add_special_tokens=True)
            for row,ids in zip(batch,encoded['input_ids']):
                key=row['split']+'/'+field;n=len(ids)
                length_counts[key]['rows']+=1
                length_counts[key]['over_256_tokens']+=int(n>256)
                length_counts[key]['over_512_tokens']+=int(n>512)
                maximum[key]=max(maximum[key],n)
    print('Counting untruncated token lengths on CPU...',flush=True)
    for row in rows():
        row_counts[row['split']]+=1;batch.append(row)
        if len(batch)==64:count_lengths(batch);batch=[]
    if batch:count_lengths(batch)
    for split,counts in recorded['counts_by_split_and_source_label'].items():
        if row_counts[split]!=sum(counts.values()):raise ValueError('Row count mismatch')
    print('Screening bounded cross-split lexical similarities...',flush=True)
    connection=sqlite3.connect(args.output_dir/'lexical_screen.sqlite')
    try:lexical=screen(connection,rows())
    finally:connection.close()
    report={'preparation_summary_sha256':hash_file(local),'script_sha256':hash_file(Path(__file__)),
            'tokenizer_revision':REVISION,'encoder_window_tokens_including_specials':256,
            'token_lengths':{key:dict(v,maximum_tokens=maximum[key]) for key,v in length_counts.items()},
            'lexical_screen':lexical,'training_performed':False,'model_scores_computed':False,
            'scope':'Dataset QA only; aggregate reserved-test lengths/similarity inspected. No efficacy measurement. No raw text printed.'}
    (args.output_dir/'readiness_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
