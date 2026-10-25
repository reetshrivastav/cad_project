from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from llmail_short_model import balanced_weights,metrics,fit_export,PARAMS

class FakeEmbedder:
    max_seq_length=256
    def __init__(self):self.seen=[]
    def tokenizer(self,texts,**kwargs):return {'input_ids':[[0]*len(t.split()) for t in texts]}
    def encode(self,texts,**kwargs):
        self.seen.extend(texts)
        return np.asarray([[float('positive' in t),float('negative' in t),1.] for t in texts],dtype=np.float32)

class ShortModelTests(unittest.TestCase):
    def test_balanced_training_weights(self):
        y=np.asarray([1,1,1,0]);w=balanced_weights(y)
        self.assertAlmostEqual(w[y==0].sum(),w[y==1].sum())

    def test_majority_accuracy_does_not_hide_poor_balance(self):
        rows=[{'source_attack_attempt':'True'}]*9+[{'source_attack_attempt':'False'}]
        result=metrics(rows,np.ones(10))
        self.assertEqual(result['source_annotation_accuracy'],.9)
        self.assertEqual(result['balanced_accuracy'],.5)
        self.assertEqual(result['source_negative_specificity'],0)

    def test_export_never_encodes_test_and_model_roundtrips(self):
        rows=[]
        for split in ('train','validation','test'):
            for label,word in [('True','positive'),('False','negative')]:
                rows.append(dict(id=split+label,split=split,component_sha256=split,source_attack_attempt=label,task=split+' task',untrusted_content=word))
        embedder=FakeEmbedder()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'model'
            report,metadata=fit_export(target,rows,embedder,dict(PARAMS,n_estimators=2))
            self.assertEqual(report['test_inputs_encoded'],0)
            self.assertFalse(any('test task'==t for t in embedder.seen))
            from xgboost import XGBClassifier
            model=XGBClassifier();model.load_model(target/'pair.ubj')
            self.assertEqual(model.n_features_in_,13)
            self.assertEqual(len(metadata['training_ids']),2)

    def test_long_inputs_are_rejected(self):
        from llmail_short_model import encode
        with self.assertRaisesRegex(ValueError,'no truncation'):
            encode([dict(task='task',untrusted_content='word '*257)],FakeEmbedder())
