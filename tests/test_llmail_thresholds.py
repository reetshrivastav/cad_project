import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from llmail_thresholds import choose_threshold,at_threshold
from analyze_llmail_benign import analyze
from evaluate_llmail_reserved import test_rows as load_test_rows
from context_pair_v2 import digest

class ThresholdTests(unittest.TestCase):
    def test_validation_only_and_float32_ties(self):
        p=float(np.float32(.75));rows=[dict(split='validation',source_attack_attempt='False',probability=p)]*10
        threshold=choose_threshold(rows)
        self.assertGreater(threshold,p)
        result=at_threshold(rows,np.asarray([p]*10,dtype=np.float32),threshold)
        self.assertEqual(result['fp'],0)
        bad=copy.deepcopy(rows);bad[0]['split']='test'
        with self.assertRaises(ValueError):choose_threshold(bad)

    def test_cutoff_uses_negative_scores_not_positive_labels(self):
        negatives=[dict(split='validation',source_attack_attempt='False',probability=.7+i*.01) for i in range(10)]
        positives=[dict(split='validation',source_attack_attempt='True',probability=.1)]
        threshold=choose_threshold(negatives+positives);positives[0]['probability']=.99
        self.assertEqual(choose_threshold(negatives+positives),threshold)

    def test_benign_evidence_reconciles(self):
        result=analyze(ROOT/'reports/evidence/llmail_benign_20261023/llmail_benign_diagnostic_v1.json')
        self.assertEqual(result['eligible_count'],160)
        self.assertEqual(result['models']['pair']['flagged_publisher_benign'],20)

    def test_development_overlap_rejected_before_test_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.jsonl';path.write_text(json.dumps(dict(id='seen',split='test',source_attack_attempt='True'))+'\n')
            summary={'files':{'test':{'sha256':digest(path)}},'retained_counts':{'test':{'True':1}}}
            with self.assertRaisesRegex(ValueError,'test IDs'):
                load_test_rows(path,{'training_ids':['seen'],'validation_ids':[]},summary)

    def test_frozen_policy_matches_recorded_validation_scores(self):
        import tarfile
        policy=json.loads((ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json').read_text())
        with tarfile.open(ROOT/'reports/evidence/llmail_short_training_20261023/llmail-short-training-v1.tar.gz') as archive:
            report=json.load(archive.extractfile('models/llmail_short_baseline_v1/training_report.json'))
        for mode,record in report['models'].items():
            rows=[r for r in record['observations'] if r['split']=='validation']
            self.assertEqual(choose_threshold(rows),policy['thresholds'][mode])
            self.assertEqual(at_threshold(rows,[r['probability'] for r in rows],policy['thresholds'][mode]),policy['validation'][mode])
