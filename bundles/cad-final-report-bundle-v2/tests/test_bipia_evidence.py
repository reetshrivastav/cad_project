import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_bipia_evaluation as analysis


class BIPIAEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'reports/evidence/bipia_scoring_20261022/bipia_controlled_native_v1.json').read_text())

    def test_negative_result_and_control_are_preserved(self):
        result = analysis.verify(self.data)
        self.assertEqual(result['verified_rows'], 76)
        self.assertEqual(result['normal']['quarantine'], 1)
        self.assertEqual(result['normal']['sandbox'], 2)
        self.assertEqual(result['normal']['full'], 72)
        self.assertEqual(result['counterfactual_high_pressure']['quarantine'], 2)
        self.assertEqual(result['counterfactual_high_pressure']['full'], 72)
        self.assertEqual(result['changed_decision_ids'], ['BIPIA-TEXT-034'])
        self.assertEqual(result['clean_controls'][0]['normal_tier'], 'full')

    def test_corpus_and_source_changes_are_rejected(self):
        for field in ('corpus_sha256', 'source_commit', 'classifier_sha256'):
            data = copy.deepcopy(self.data)
            data[field] = 'different'
            with self.assertRaises(ValueError):
                analysis.verify(data)

    def test_row_and_metric_inconsistencies_are_rejected(self):
        for change in ('prompt', 'tier', 'metric'):
            data = copy.deepcopy(self.data)
            if change == 'prompt':
                data['rows'][1]['prompt'] = 'modified'
            elif change == 'tier':
                data['rows'][1]['normal_tier'] = 'quarantine'
            else:
                data['metrics']['normal']['quarantine'] = 75
            with self.assertRaises(ValueError):
                analysis.verify(data)
