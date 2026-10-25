"""No-truncation short-email subset with conservative cross-split lexical cleanup."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata
import numpy as np
from check_llmail_readiness import RECORDED,REVISION,tokens,jaccard
from prepare_llmail_phase1 import hash_file
PRIORITY={'train':0,'validation':1,'test':2}
PRIME=4294967291
_rng=np.random.default_rng(42)
_A=_rng.integers(1,PRIME,size=64,dtype=np.uint64)
_B=_rng.integers(0,PRIME,size=64,dtype=np.uint64)


def bands(words):
    if not words:return []
    values=np.array([int.from_bytes(hashlib.blake2s(w.encode(),digest_size=4).digest(),'big') for w in words],dtype=np.uint64)
    signature=((values[:,None]*_A[None,:]+_B[None,:])%PRIME).min(axis=0)
    return [str(i)+':'+signature[i*4:(i+1)*4].astype('>u8').tobytes().hex() for i in range(16)]


def normalized_text(text):
    return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())


def cleanup(connection,records,candidate_cap=500,pair_budget=2_000_000):
    connection.executescript('CREATE TABLE docs(id TEXT PRIMARY KEY, split TEXT, words TEXT); CREATE TABLE buckets(band TEXT,id TEXT,split TEXT); CREATE INDEX bucket_index ON buckets(band); CREATE TABLE exact_keys(kind TEXT,key TEXT,id TEXT,split TEXT); CREATE INDEX exact_index ON exact_keys(kind,key); CREATE TABLE excluded(id TEXT PRIMARY KEY);')
    stats=Counter();cross_pairs=Counter()
    def exclude(a_id,a_split,b_id,b_split):
        if a_split==b_split:return
        lower=a_id if PRIORITY[a_split]<PRIORITY[b_split] else b_id
        connection.execute('INSERT OR IGNORE INTO excluded VALUES (?)',(lower,))
    for row in records:
        words=tokens(row['untrusted_content']);serialized=json.dumps(sorted(words),ensure_ascii=False)
        exacts={'normalized_text':hashlib.sha256(normalized_text(row['untrusted_content']).encode()).hexdigest(),
                'token_bag':hashlib.sha256(serialized.encode()).hexdigest()}
        for kind,key in exacts.items():
            for other_id,other_split in connection.execute('SELECT id,split FROM exact_keys WHERE kind=? AND key=? AND split!=?',(kind,key,row['split'])).fetchall():
                exclude(row['id'],row['split'],other_id,other_split);stats[kind+'_cross_split_pairs']+=1
        bb=bands(words);candidates=set()
        for band in bb:
            candidates.update(connection.execute('SELECT id,split FROM buckets WHERE band=? AND split!=?',(band,row['split'])).fetchall())
        stats['lsh_candidates']+=len(candidates)
        conservative=len(candidates)>candidate_cap or stats['verified_comparisons']>=pair_budget
        if conservative:stats['conservative_candidate_rows']+=1
        for other_id,other_split in sorted(candidates):
            if conservative or stats['verified_comparisons']>=pair_budget:
                exclude(row['id'],row['split'],other_id,other_split);stats['conservatively_excluded_candidate_edges']+=1
                continue
            other_words=json.loads(connection.execute('SELECT words FROM docs WHERE id=?',(other_id,)).fetchone()[0])
            stats['verified_comparisons']+=1
            if jaccard(words,set(other_words))>=.8:
                exclude(row['id'],row['split'],other_id,other_split)
                stats['verified_jaccard_pairs']+=1;cross_pairs['/'.join(sorted((row['split'],other_split)))]+=1
        connection.execute('INSERT INTO docs VALUES (?,?,?)',(row['id'],row['split'],serialized))
        connection.executemany('INSERT INTO buckets VALUES (?,?,?)',[(band,row['id'],row['split']) for band in bb])
        connection.executemany('INSERT INTO exact_keys VALUES (?,?,?,?)',[(kind,key,row['id'],row['split']) for kind,key in exacts.items()])
        stats['rows']+=1
        if stats['rows']%5000==0:connection.commit();print(f"Cleanup: {stats['rows']} short emails",flush=True)
    connection.commit()
    # Exact keys have been fully indexed, including rows later excluded. No normalized
    # text/token-bag key may survive on both sides of a split boundary.
    leaked=connection.execute('SELECT 1 FROM exact_keys e LEFT JOIN excluded x ON e.id=x.id WHERE x.id IS NULL GROUP BY kind,key HAVING COUNT(DISTINCT split)>1 LIMIT 1').fetchone()
    if leaked:raise ValueError('Normalized exact cross-split leakage survived cleanup')
    stats['excluded_rows']=connection.execute('SELECT COUNT(*) FROM excluded').fetchone()[0]
    return {'counts':dict(stats),'verified_jaccard_pairs_by_split':dict(cross_pairs),'surviving_normalized_exact_keys_cross_splits':0,
            'scope':'Complete normalized-text/token-bag exact cleanup among short rows; approximate 64-permutation 16x4 MinHash candidates with unigram Jaccard >=0.8. Overflow/budget candidates conservatively excluded rather than skipped. Does not establish absence of semantic/template leakage.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepared-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('Use a fresh output directory')
    recorded=json.loads(RECORDED.read_text())
    if hash_file(args.prepared_dir/'preparation_summary.json')!=hash_file(RECORDED):raise ValueError('Unexpected source preparation')
    for split,record in recorded['files'].items():
        path=args.prepared_dir/(split+'.jsonl')
        if hash_file(path)!=record['sha256'] or path.stat().st_size!=record['bytes']:raise ValueError('Split checksum mismatch')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2',revision=REVISION,local_files_only=True)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    short_counts={s:Counter() for s in PRIORITY};long_counts={s:Counter() for s in PRIORITY}
    short_paths={s:args.output_dir/('eligible_'+s+'.jsonl') for s in PRIORITY}
    print('Selecting rows whose task AND full email each fit 256 tokens; no truncation...',flush=True)
    for split in PRIORITY:
        batch=[]
        with (args.prepared_dir/(split+'.jsonl')).open() as source,short_paths[split].open('x') as out:
            def flush():
                if not batch:return
                task=tokenizer([r['task'] for r in batch],truncation=False,add_special_tokens=True)['input_ids']
                content=tokenizer([r['untrusted_content'] for r in batch],truncation=False,add_special_tokens=True)['input_ids']
                for row,t,c in zip(batch,task,content):
                    if row['split']!=split:raise ValueError('Unexpected split field')
                    if max(len(t),len(c))<=256:
                        out.write(json.dumps(row)+'\n');short_counts[split][row['source_attack_attempt']]+=1
                    else:long_counts[split][row['source_attack_attempt']]+=1
                batch.clear()
            for line in source:
                batch.append(json.loads(line))
                if len(batch)==64:flush()
            flush()
    def records():
        for split in PRIORITY:
            with short_paths[split].open() as handle:
                for line in handle:yield json.loads(line)
    connection=sqlite3.connect(args.output_dir/'cleanup.sqlite')
    try:
        screened=cleanup(connection,records());kept={s:Counter() for s in PRIORITY};removed={s:Counter() for s in PRIORITY}
        excluded={r[0] for r in connection.execute('SELECT id FROM excluded')}
        for split in PRIORITY:
            with short_paths[split].open() as source,(args.output_dir/(split+'.jsonl')).open('x') as out:
                for line in source:
                    row=json.loads(line);label=row['source_attack_attempt']
                    if row['id'] in excluded:removed[split][label]+=1
                    else:kept[split][label]+=1;out.write(line)
    finally:connection.close()
    for split in PRIORITY:
        if sum(kept[split].values())+sum(removed[split].values())!=sum(short_counts[split].values()):raise ValueError('Cleanup counts mismatch')
    report={'source_preparation_sha256':hash_file(RECORDED),'script_sha256':hash_file(Path(__file__)),
            'tokenizer_revision':REVISION,'window_including_specials':256,
            'eligible_short_counts':{s:dict(c) for s,c in short_counts.items()},'excluded_long_counts':{s:dict(c) for s,c in long_counts.items()},
            'lexical_cleanup':screened,'removed_for_overlap':{s:dict(c) for s,c in removed.items()},'retained_counts':{s:dict(c) for s,c in kept.items()},
            'files':{s:{'sha256':hash_file(args.output_dir/(s+'.jsonl')),'bytes':(args.output_dir/(s+'.jsonl')).stat().st_size} for s in PRIORITY},
            'training_performed':False,'scope':'Short-email source-annotation baseline preparation only. Long emails excluded with explicit coverage counts. Not a general prompt-injection safety evaluation. Higher-priority test > validation > train retained; no rows moved between original team splits.'}
    (args.output_dir/'short_baseline_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
