"""Experimental task/content pair model utilities; not part of live routing."""
import hashlib
import math
from pathlib import Path

import numpy as np

LABELS={'allow_task':0,'review_redirection':1}
MODES=('pair','task_only','content_only')
EMBEDDER_NAME='all-MiniLM-L6-v2'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_input(row):
    for name in ('task','untrusted_content'):
        value=row.get(name)
        if not isinstance(value,str) or not value.strip():
            raise ValueError(f'{name} must be a nonempty string')
        if len(value)>10000:raise ValueError(f'{name} exceeds prototype character limit')


def pair_features(task,content,mode='pair'):
    task=np.asarray(task,dtype=np.float32);content=np.asarray(content,dtype=np.float32)
    if task.shape!=content.shape or task.ndim!=2:raise ValueError('Embedding shape mismatch')
    if not np.isfinite(task).all() or not np.isfinite(content).all():raise ValueError('Nonfinite embedding')
    if mode=='task_only':return task
    if mode=='content_only':return content
    if mode!='pair':raise ValueError('Unknown feature mode')
    return np.concatenate([task,content,np.abs(task-content),task*content,
                           np.sum(task*content,axis=1,keepdims=True)],axis=1)


def encode_inputs(rows,embedder):
    # Only these two strings reach the encoder. IDs, labels, groups, scenario
    # types and split assignments are not input features.
    for row in rows:validate_input(row)
    texts=[r['task'] for r in rows]+[r['untrusted_content'] for r in rows]
    tokenized=embedder.tokenizer(texts,truncation=False,add_special_tokens=True)
    if any(len(ids)>embedder.max_seq_length for ids in tokenized['input_ids']):
        raise ValueError('Input exceeds MiniLM limit; no silent truncation')
    vectors=embedder.encode(texts,convert_to_numpy=True,normalize_embeddings=True,
                            show_progress_bar=False,batch_size=32)
    return np.asarray(vectors[:len(rows)],dtype=np.float32),np.asarray(vectors[len(rows):],dtype=np.float32)


def load_embedder(revision=None):
    import torch
    from sentence_transformers import SentenceTransformer
    if not torch.cuda.is_available():raise ValueError('CUDA required for lab v2 prototype')
    kwargs={'revision':revision} if revision else {}
    embedder=SentenceTransformer(EMBEDDER_NAME,device='cuda',**kwargs).half()
    if str(next(embedder.parameters()).dtype)!='torch.float16':raise ValueError('Expected FP16 embeddings')
    commit=getattr(embedder._first_module().auto_model.config,'_commit_hash',None)
    if not commit:raise ValueError('Embedding checkpoint revision unavailable; cannot record reproducible model')
    if revision and commit!=revision:raise ValueError('Embedding revision differs from training')
    return embedder,commit


def outcome_metrics(rows,probabilities):
    if len(rows)!=len(probabilities) or not rows:raise ValueError('Metrics require matching nonempty observations')
    tp=fp=tn=fn=0
    for row,p in zip(rows,probabilities):
        if not math.isfinite(float(p)) or not 0<=p<=1:raise ValueError('Invalid review probability')
        expected=LABELS[row['label']];review=p>=.5
        tp+=int(expected==1 and review);fn+=int(expected==1 and not review)
        fp+=int(expected==0 and review);tn+=int(expected==0 and not review)
    return {'count':len(rows),'threshold':.5,'rule':'review_probability >= 0.5',
            'true_review':tp,'false_review':fp,'correct_allow':tn,'missed_review':fn,
            'workflow_proxy_accuracy':(tp+tn)/len(rows),
            'review_coverage':tp/(tp+fn) if tp+fn else None,
            'false_review_rate':fp/(fp+tn) if fp+tn else None,
            'scope':'Synthetic workflow-proxy labels, not deployment accuracy, malicious-intent truth or downstream attack success.'}
