import csv
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import evaluate_benign_candidates as evaluation

LABELS = ROOT / 'reports/evidence/heldout_ai_annotation_20261022/cad-heldout-label-review-ai.csv'


class BenignEvaluationTests(unittest.TestCase):
    def test_all_uploaded_annotations_match_frozen_inputs(self):
        rows = evaluation.load_labels(LABELS)
        self.assertEqual(len(rows), 200)
        self.assertTrue(all(r['label'] == 'benign' and 'AI-only' in r['reviewer'] for r in rows))

    def test_changed_prompt_duplicate_id_and_missing_review_are_rejected(self):
        for field, value in [('prompt', 'modified prompt'), ('id', 'ALPACA-REVIEW-0002'),
                             ('reviewer', ''), ('label', '')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                rows = evaluation.load_labels(LABELS)
                rows[0][field] = value
                path = Path(directory) / 'labels.csv'
                with path.open('w', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaises(ValueError):
                    evaluation.load_labels(path)

    def test_threshold_boundaries_and_errors_are_preserved(self):
        risks = iter([.2499, .25, .35, .65, .75, float('nan')])
        rows = [{'id': str(i), 'label': 'benign', 'prompt': 'example'} for i in range(6)]
        result = evaluation.score_rows(rows, lambda _: {'risk': next(risks)})
        self.assertEqual([r.get('normal_tier') for r in result],
                         ['full', 'full', 'sandbox', 'sandbox', 'quarantine', None])
        self.assertEqual([r.get('counterfactual_high_pressure_tier') for r in result],
                         ['full', 'sandbox', 'sandbox', 'quarantine', 'quarantine', None])
        metrics = evaluation.policy_metrics(result, 'normal_tier')
        self.assertEqual(metrics['labeled_benign_total'], 6)
        self.assertEqual(metrics['successfully_scored'], 5)
        self.assertEqual(metrics['scoring_errors'], 1)
        self.assertEqual(metrics['quarantine']['rate'], .2)
        self.assertEqual(metrics['sandbox']['rate'], .4)
        self.assertEqual(metrics['any_restriction']['rate'], .6)

    def test_excluded_rows_are_not_scored_and_nonbenign_not_in_false_positive_denominator(self):
        rows = [{'label': 'exclude', 'prompt': 'not sent'}, {'label': 'injection', 'prompt': 'scored'}]
        calls = []
        def score(prompt):
            calls.append(prompt)
            return {'risk': .9}
        result = evaluation.score_rows(rows, score)
        self.assertEqual(calls, ['scored'])
        self.assertTrue(result[0]['excluded'])
        metrics = evaluation.policy_metrics(result, 'normal_tier')
        self.assertEqual(metrics['labeled_benign_total'], 0)
        self.assertIsNone(metrics['quarantine']['rate'])
        self.assertIsNone(metrics['quarantine']['wilson_95_interval'])

    def test_wilson_zero_events_does_not_claim_zero_population_risk(self):
        low, high = evaluation.wilson(0, 200)
        self.assertAlmostEqual(low, 0)
        self.assertGreater(high, .018)
        self.assertLess(high, .020)
