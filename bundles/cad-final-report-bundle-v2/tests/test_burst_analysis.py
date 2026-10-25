import importlib.util
from pathlib import Path
import json
import unittest

spec = importlib.util.spec_from_file_location(
    'burst_analysis', Path(__file__).resolve().parents[1] / 'scripts/analyze_gpu_burst.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class BurstEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / 'reports/evidence/native_burst_20261018'
        self.data = json.loads((self.root / 'gpu_burst_calibration_native_v1.json').read_text())
        self.meta = json.loads((self.root / 'lab_native_v1_metadata.json').read_text())

    def test_rejects_mismatched_classifier_metadata(self):
        self.meta['artifact_sha256']['classifier.joblib'] = 'wrong'
        with self.assertRaises(ValueError):
            analysis.validate_metadata(self.data, self.meta)

    def test_all_supplied_trial_counters_reconcile(self):
        result = analysis.summarize(self.data, self.meta)
        direct, gateway = result['trials']
        self.assertTrue(all(t['counter_usage_matches'] for t in result['trials']))
        self.assertEqual(direct['backend_generation_tokens_delta'] - gateway['backend_generation_tokens_delta'], 14336)
        self.assertEqual(direct['backend_prompt_tokens_delta'] - gateway['backend_prompt_tokens_delta'], 616)
        self.assertEqual(direct['peak_waiting'], 13)
        self.assertEqual(gateway['peak_waiting'], 0)
        self.assertIsNone(gateway['benign_p99_http_ms'])
        self.assertEqual(gateway['request_policy_counts'], {'normal': 16})

    def test_controls_share_workload_model_and_reconcile_counters(self):
        root = self.root.parent / 'static_adaptive_controls_20261018'
        configs = []
        for mode in ('static', 'adaptive'):
            data = json.loads((root / f'gpu_{mode}_control_native_v1.json').read_text())
            self.assertEqual(data['gateway_status']['routing_mode'], mode)
            result = analysis.summarize(data, self.meta)['trials'][0]
            self.assertTrue(result['counter_usage_matches'])
            self.assertEqual(result['backend_generation_tokens_delta'], 128)
            self.assertEqual(result['demands_quarantined'], 8)
            self.assertEqual(result['peak_waiting'], 0)
            configs.append({k: v for k, v in data['configuration'].items()
                            if k not in ('require_routing_mode', 'output')})
        self.assertEqual(configs[0], configs[1])
