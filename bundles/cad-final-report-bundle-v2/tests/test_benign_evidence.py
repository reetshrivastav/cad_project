import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_benign_evaluation as analysis


class BenignEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'reports/evidence/benign_ai_scoring_20261022/benign_ai_labeled_native_v1.json').read_text())

    def test_all_rows_and_restrictions_reconcile(self):
        result = analysis.verify(self.data)
        self.assertEqual(result['verified_rows'], 200)
        self.assertEqual(result['metrics_normal']['quarantine']['count'], 4)
        self.assertEqual(result['metrics_normal']['sandbox']['count'], 9)
        self.assertEqual(len(result['affected_rows']), 14)
        self.assertEqual(len(result['changed_decision_ids']), 3)

    def test_input_and_provenance_changes_are_rejected(self):
        for field, value in [('labels_sha256', 'different'), ('annotation_provenance', 'human reviewed')]:
            data = copy.deepcopy(self.data)
            data[field] = value
            with self.assertRaises(ValueError):
                analysis.verify(data)

    def test_tier_probability_and_metric_inconsistencies_are_rejected(self):
        for change in ('tier', 'probability', 'metric'):
            data = copy.deepcopy(self.data)
            if change == 'tier':
                data['rows'][0]['normal_tier'] = 'quarantine'
            elif change == 'probability':
                data['rows'][0]['probabilities']['benign'] = .1
            else:
                data['metrics_normal']['quarantine']['count'] = 0
            with self.assertRaises(ValueError):
                analysis.verify(data)
