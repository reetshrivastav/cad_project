import copy
from collections import defaultdict
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import context_pair_v2 as pair
import prepare_context_v2 as preparation
import train_context_v2 as training
import evaluate_context_v2 as evaluation


class FakeEmbedder:
    max_seq_length=256
    def __init__(self):self.seen=[]
    def tokenizer(self,texts,**kwargs):return {'input_ids':[list(range(len(t.split()))) for t in texts]}
    def encode(self,texts,**kwargs):
        self.seen.extend(texts)
        vectors=[]
        for text in texts:
            v=np.asarray([float('Summarize only' in text or 'Summarize the status' in text),
                          float('Extract only' in text),float('Identify and explain' in text),
                          float('For a security audit' in text),
                          float('Ignore the requested' in text or 'disregard the user task' in text),1.],dtype=np.float32)
            vectors.append(v/np.linalg.norm(v))
        return np.asarray(vectors)


class ContextV2Tests(unittest.TestCase):
    def test_group_splits_and_contrasting_same_content_are_real(self):
        audit,rows=preparation.load_dataset()
        self.assertEqual(audit['counts_by_split'],{'train':280,'validation':60,'test':60})
        preparation.validate_dataset(rows)
        labels=defaultdict(set)
        for row in rows:labels[row['untrusted_content']].add(row['label'])
        self.assertEqual(sum(len(v)==2 for v in labels.values()),80)
        self.assertEqual(len(rows),400)

    def test_group_leak_and_duplicate_pairs_are_rejected(self):
        _,rows=preparation.load_dataset()
        bad=copy.deepcopy(rows);bad[0]['split']='validation' if bad[0]['split']=='train' else 'train'
        with self.assertRaisesRegex(ValueError,'leaks'):preparation.validate_dataset(bad)
        bad=copy.deepcopy(rows);extra=dict(bad[0],id='new-id');bad.append(extra)
        with self.assertRaisesRegex(ValueError,'Duplicate input pair'):preparation.validate_dataset(bad)

    def test_encoder_receives_only_two_text_fields_and_never_truncates(self):
        _,rows=preparation.load_dataset();rows=rows[:2]
        embedder=FakeEmbedder();a,b=pair.encode_inputs(rows,embedder)
        self.assertEqual(embedder.seen,[r['task'] for r in rows]+[r['untrusted_content'] for r in rows])
        self.assertEqual(pair.pair_features(a,b).shape,(2,25))
        unlabeled=[{k:r[k] for k in ('task','untrusted_content')} for r in rows]
        x,y=pair.encode_inputs(unlabeled,FakeEmbedder())
        np.testing.assert_array_equal(x,a)
        np.testing.assert_array_equal(y,b)
        with self.assertRaisesRegex(ValueError,'shape'):pair.pair_features(a,b[:1])
        embedder.max_seq_length=1
        with self.assertRaisesRegex(ValueError,'no silent truncation'):pair.encode_inputs(rows,embedder)

    def test_export_roundtrip_and_no_test_input_in_fitting_or_validation(self):
        audit,rows=preparation.load_dataset();embedder=FakeEmbedder()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new-model'
            params=dict(training.PARAMS,n_estimators=3,learning_rate=.5)
            report,metadata=training.fit_export(output,audit,rows,embedder,'test-only-fake-revision',params)
            eligible=[r for r in rows if r['split']!='test']
            self.assertEqual(embedder.seen,[r['task'] for r in eligible]+[r['untrusted_content'] for r in eligible])
            test_tasks={r['task'] for r in rows if r['split']=='test'}
            self.assertFalse(test_tasks&set(embedder.seen))
            self.assertEqual(report['test_inputs_encoded'],0)
            self.assertEqual(len(metadata['training_ids']),280)
            self.assertEqual(len(metadata['validation_ids']),60)
            result=evaluation.evaluate(output,audit,rows,FakeEmbedder())
            for mode in pair.MODES:
                self.assertEqual(result['models'][mode]['metrics']['count'],60)
                self.assertEqual(len(result['models'][mode]['rows']),60)
            with self.assertRaisesRegex(ValueError,'not empty'):
                training.fit_export(output,audit,rows,FakeEmbedder(),'fake',params)
            with (output/'pair.ubj').open('ab') as handle:handle.write(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):evaluation.verify_metadata(output,audit)

    def test_workflow_metrics_are_explicit_and_probabilities_validated(self):
        rows=[{'label':'allow_task'},{'label':'review_redirection'},{'label':'review_redirection'}]
        result=pair.outcome_metrics(rows,[.5,.5,.2])
        self.assertEqual(result['false_review'],1)
        self.assertEqual(result['true_review'],1)
        self.assertEqual(result['missed_review'],1)
        with self.assertRaises(ValueError):pair.outcome_metrics(rows,[.5,.5,float('nan')])
