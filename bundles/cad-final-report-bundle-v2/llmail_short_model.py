"""Offline LLMail source-annotation baseline; never imported by the gateway."""
import numpy as np
from context_pair_v2 import MODES,pair_features
LABELS={'False':0,'True':1}
PARAMS=dict(n_estimators=150,max_depth=4,learning_rate=.05,subsample=.9,colsample_bytree=.9,
            objective='binary:logistic',eval_metric='logloss',random_state=42,n_jobs=2)


def development_rows(rows):
    selected=[r for r in rows if r['split'] in ('train','validation')]
    if not selected:raise ValueError('No development rows')
    ids=set();groups={}
    for row in selected:
        if row['id'] in ids:raise ValueError('Duplicate development ID')
        ids.add(row['id'])
        if row['source_attack_attempt'] not in LABELS:raise ValueError('Unsupported source annotation')
        g=row['component_sha256'];s=row['split']
        if g in groups and groups[g]!=s:raise ValueError('Component crosses splits')
        groups[g]=s
    for split in ('train','validation'):
        if {r['source_attack_attempt'] for r in selected if r['split']==split}!=set(LABELS):raise ValueError('Both source classes required in development splits')
    return selected


def encode(rows,embedder):
    texts=[r['task'] for r in rows]+[r['untrusted_content'] for r in rows]
    if any(not isinstance(t,str) or not t.strip() for t in texts):raise ValueError('Empty/non-string model input')
    if embedder.max_seq_length!=256:raise ValueError('Expected 256-token encoder window')
    lengths=embedder.tokenizer(texts,truncation=False,add_special_tokens=True)['input_ids']
    if any(len(ids)>256 for ids in lengths):raise ValueError('Long input rejected; no truncation')
    vectors=np.asarray(embedder.encode(texts,convert_to_numpy=True,normalize_embeddings=True,batch_size=32,show_progress_bar=False),dtype=np.float32)
    if vectors.ndim!=2 or len(vectors)!=len(texts) or not np.isfinite(vectors).all():raise ValueError('Invalid embeddings')
    return vectors[:len(rows)],vectors[len(rows):]


def balanced_weights(labels):
    labels=np.asarray(labels)
    counts=np.bincount(labels,minlength=2)
    if len(counts)!=2 or any(counts==0):raise ValueError('Both classes required for balanced weights')
    return len(labels)/(2*counts[labels])


def metrics(rows,probabilities):
    from sklearn.metrics import roc_auc_score,average_precision_score
    y=np.asarray([LABELS[r['source_attack_attempt']] for r in rows]);p=np.asarray(probabilities,dtype=float)
    if len(y)==0 or p.shape!=y.shape or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probabilities')
    predicted=p>=.5;tp=int(((y==1)&predicted).sum());fn=int(((y==1)&~predicted).sum())
    fp=int(((y==0)&predicted).sum());tn=int(((y==0)&~predicted).sum())
    tpr=tp/(tp+fn) if tp+fn else None;tnr=tn/(tn+fp) if tn+fp else None
    return {'count':len(y),'threshold':.5,'tp':tp,'fn':fn,'fp':fp,'tn':tn,
            'source_annotation_accuracy':(tp+tn)/len(y),
            'source_positive_recall':tpr,'source_negative_specificity':tnr,
            'balanced_accuracy':(tpr+tnr)/2 if tpr is not None and tnr is not None else None,
            'source_positive_precision':tp/(tp+fp) if tp+fp else None,
            'roc_auc':float(roc_auc_score(y,p)) if len(set(y))==2 else None,
            'average_precision':float(average_precision_score(y,p)) if any(y==1) else None,
            'scope':'Agreement with publisher automated source annotations on selectively retained short emails; not independent security accuracy or downstream attack success.'}


def fit_export(output,rows,embedder,parameters=None):
    from xgboost import XGBClassifier
    from pathlib import Path
    from context_pair_v2 import digest
    import json
    selected=development_rows(rows);output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('Output directory not empty')
    task,content=encode(selected,embedder)
    train=np.asarray([r['split']=='train' for r in selected]);y=np.asarray([LABELS[r['source_attack_attempt']] for r in selected])
    weights=balanced_weights(y[train]);parameters=parameters or PARAMS
    output.mkdir(parents=True,exist_ok=True)
    report={'test_inputs_encoded':0,'training_count':int(train.sum()),'validation_count':int((~train).sum()),'models':{},
            'always_source_positive':{s:metrics([r for r in selected if r['split']==s],np.ones(sum(r['split']==s for r in selected))) for s in ('train','validation')}}
    for mode in MODES:
        features=pair_features(task,content,mode);model=XGBClassifier(**parameters)
        model.fit(features[train],y[train],sample_weight=weights)
        if list(model.classes_)!=[0,1]:raise ValueError('Unexpected classifier class order')
        model.save_model(output/(mode+'.ubj'));p=model.predict_proba(features)[:,1]
        report['models'][mode]={s:metrics([r for r in selected if r['split']==s],p[train if s=='train' else ~train]) for s in ('train','validation')}
        report['models'][mode]['observations']=[dict(id=r['id'],split=r['split'],source_attack_attempt=r['source_attack_attempt'],probability=float(prob)) for r,prob in zip(selected,p)]
    (output/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report,{'training_ids':[r['id'] for r in selected if r['split']=='train'],
                   'validation_ids':[r['id'] for r in selected if r['split']=='validation'],
                   'embedding_width':int(task.shape[1]),'hyperparameters':parameters,
                   'weighting':'Inverse class frequency from training labels only: n/(2*n_class).',
                   'artifact_sha256':{name:digest(output/name) for name in ('pair.ubj','task_only.ubj','content_only.ubj','training_report.json')}}
