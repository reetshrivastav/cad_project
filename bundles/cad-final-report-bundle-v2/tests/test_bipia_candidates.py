import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_bipia_candidates as preparation
import evaluate_bipia_candidates as evaluation


class BIPIAPreparationTests(unittest.TestCase):
    def test_pinned_source_reproduces_all_frozen_contexts(self):
        audit, rows = evaluation.load_candidates()
        self.assertEqual(audit['source_attack_count'], 75)
        self.assertEqual(audit['retained_attack_count'], 75)
        self.assertEqual(len(rows), 76)
        self.assertEqual(audit['excluded_rows'], [])
        self.assertEqual(len(audit['retained_categories']), 15)
        self.assertTrue(all(n==5 for n in audit['retained_categories'].values()))
        self.assertEqual(rows[0]['label'], 'benign')
        for row in rows[1:]:
            self.assertEqual(row['prompt'], preparation.PREFIX+'\n'+row['attack_text']+preparation.SUFFIX)
            self.assertEqual(row['label'], 'injection')

    def test_mutated_corpus_stops_before_model_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changed.jsonl'
            path.write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                evaluation.load_candidates(path)

    def test_coverage_distinguishes_quarantine_sandbox_errors_and_control(self):
        rows = [{'label':'injection', 'category':'sample', 'normal_tier':'quarantine',
                 'counterfactual_high_pressure_tier':'quarantine'},
                {'label':'injection', 'category':'sample', 'normal_tier':'full',
                 'counterfactual_high_pressure_tier':'sandbox'},
                {'label':'injection', 'category':'sample', 'error':'failure'},
                {'label':'benign', 'normal_tier':'full', 'counterfactual_high_pressure_tier':'full'}]
        metrics = evaluation.metrics(rows)
        self.assertEqual(metrics['normal']['offered'], 3)
        self.assertEqual(metrics['normal']['scored'], 2)
        self.assertEqual(metrics['normal']['scoring_errors'], 1)
        self.assertEqual(metrics['normal']['quarantine_coverage'], .5)
        self.assertEqual(metrics['normal']['any_restriction_coverage'], .5)
        self.assertEqual(metrics['counterfactual_high_pressure']['any_restriction_coverage'], 1)
        self.assertEqual(len(metrics['clean_controls']), 1)

    def test_all_failures_have_no_success_rate(self):
        result = evaluation.coverage([{'error':'failure'}], 'normal_tier')
        self.assertEqual(result['scoring_errors'], 1)
        self.assertIsNone(result['quarantine_coverage'])
