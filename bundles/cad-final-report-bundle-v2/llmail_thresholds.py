"""Validation-only operating-cutoff selection; not probability calibration."""
import math
import numpy as np
from llmail_short_model import metrics


def choose_threshold(rows,max_source_negative_flag_rate=.10):
    if not 0<=max_source_negative_flag_rate<1:raise ValueError('Invalid flag-rate target')
    if any(r['split']!='validation' for r in rows):raise ValueError('Only validation observations accepted')
    negatives=[]
    for row in rows:
        p=float(row['probability'])
        if not math.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid probability')
        if row['source_attack_attempt']=='False':negatives.append(p)
        elif row['source_attack_attempt']!='True':raise ValueError('Invalid source label')
    if not negatives:raise ValueError('No validation negatives')
    budget=math.floor(max_source_negative_flag_rate*len(negatives))
    threshold=.5
    if sum(p>=threshold for p in negatives)>budget:
        threshold=max(.5,float(np.nextafter(sorted(negatives,reverse=True)[budget],np.inf)))
    if threshold>1:raise ValueError('Target infeasible with an in-range cutoff')
    return threshold


def at_threshold(rows,probabilities,threshold):
    if not 0<=threshold<=1:raise ValueError('Invalid threshold')
    p=np.asarray(probabilities,dtype=np.float64);result=metrics(rows,p)
    y=np.asarray([r['source_attack_attempt']=='True' for r in rows]);flag=p>=float(threshold)
    tp=int((y&flag).sum());fn=int((y&~flag).sum());fp=int((~y&flag).sum());tn=int((~y&~flag).sum())
    tpr=tp/(tp+fn) if tp+fn else None;tnr=tn/(tn+fp) if tn+fp else None
    result.update(threshold=float(threshold),tp=tp,fn=fn,fp=fp,tn=tn,
                  source_annotation_accuracy=(tp+tn)/len(y),source_positive_recall=tpr,
                  source_negative_specificity=tnr,balanced_accuracy=(tpr+tnr)/2 if tpr is not None and tnr is not None else None,
                  source_positive_precision=tp/(tp+fp) if tp+fp else None)
    return result
