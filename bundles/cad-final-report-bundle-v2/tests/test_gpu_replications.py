import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_gpu_replications as analysis


class ReplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = ROOT / 'reports/evidence/replication_v1_20261021'
        cls.records = {key: json.loads((folder / f'{key}.json').read_text()) for key in analysis.ORDER}
        cls.metadata = json.loads((ROOT / 'reports/evidence/native_burst_20261018/lab_native_v1_metadata.json').read_text())

    def test_all_nine_runs_reconcile_and_retain_three_units_per_condition(self):
        result = analysis.analyze(self.records, self.metadata)
        self.assertTrue(result['all_counters_reconcile'])
        self.assertTrue(result['order_matches_protocol'])
        for condition, row in result['conditions'].items():
            self.assertEqual(row['runs'], 3)
            self.assertEqual(row['benign_completed'], 24)
            self.assertEqual(row['benign_failed'], 0)
            self.assertIsNone(row['benign_p99_http_ms'])
            self.assertEqual(row['backend_generation_tokens_delta'], 43392 if condition == 'direct' else 384)
        for row in result['runs']:
            self.assertTrue(row['verified_expected_outcomes'])
            self.assertTrue(row['initial_idle_zero_token_counters'])
            self.assertTrue(row['recorded_cache_config_matches'])

    def test_missing_run_and_wrong_mode_are_rejected(self):
        data = dict(self.records)
        del data['b3_static']
        with self.assertRaisesRegex(ValueError, 'nine'):
            analysis.analyze(data, self.metadata)
        data = copy.deepcopy(self.records)
        data['b1_static']['gateway_status']['routing_mode'] = 'adaptive'
        with self.assertRaisesRegex(ValueError, 'mode mismatch'):
            analysis.analyze(data, self.metadata)

    def test_changed_workload_and_code_are_rejected(self):
        for field, value in [('script_sha256', 'different'), ('configuration', dict(self.records['b2_direct']['configuration'], attack_tokens=1024))]:
            data = copy.deepcopy(self.records)
            data['b2_direct'][field] = value
            with self.assertRaises(ValueError):
                analysis.analyze(data, self.metadata)

    def test_unexpected_request_and_counter_mismatch_remain_visible(self):
        data = copy.deepcopy(self.records)
        row = data['b3_static']['trials'][0]['requests'][0]
        self.assertEqual(row['kind'], 'demand')
        row['status'] = 200
        row['body'] = {'choices': [{'message': {'content': 'unexpected'}}],
                       'usage': {'prompt_tokens': 42, 'completion_tokens': 1}}
        result = analysis.analyze(data, self.metadata)
        self.assertFalse(result['all_counters_reconcile'])
        trial = next(r for r in result['runs'] if r['run_id'] == 'b3_static')
        self.assertFalse(trial['verified_expected_outcomes'])
        self.assertEqual(trial['demands_quarantined'], 7)
