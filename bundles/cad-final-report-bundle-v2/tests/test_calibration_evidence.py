import importlib.util
import json
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('policy_analysis', root / 'scripts/analyze_policy_calibration.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)
spec2 = importlib.util.spec_from_file_location('sandbox_check', root / 'scripts/check_sandbox_live.py')
sandbox = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(sandbox)


class CalibrationEvidenceTests(unittest.TestCase):
    def test_supplied_negative_result_and_candidate(self):
        data = json.loads((root / 'reports/evidence/policy_calibration_20261018/policy_candidate_calibration_native_v1.json').read_text())
        meta = json.loads((root / 'reports/evidence/native_burst_20261018/lab_native_v1_metadata.json').read_text())
        result = analysis.analyze(data, meta)
        self.assertEqual(result['normal_tier_counts'], {'full': 32, 'sandbox': 4, 'quarantine': 64})
        self.assertEqual(result['changed_decisions'], 0)
        self.assertEqual(sandbox.choose_candidate(data)['id'], 'P04-S01')
        for family in result['families']:
            self.assertTrue(all(r > .98 for r in family['risks_by_repeat'][4:]))

    def test_timeout_is_not_successful_cap_completion(self):
        body = {'router_meta': {'tier': 'sandbox', 'applied_max_tokens': 256,
                               'backend_read_timeout_seconds': 5, 'risk_score': .4773}}
        result = sandbox.checks(502, body, .477339)
        self.assertTrue(result['policy_cap_applied'])
        self.assertFalse(result['completed_at_cap'])
        body['usage'] = {'completion_tokens': 257}
        self.assertFalse(sandbox.checks(200, body, .477339)['completed_at_cap'])
        body['usage']['completion_tokens'] = 256
        self.assertTrue(sandbox.checks(200, body, .477339)['completed_at_cap'])
