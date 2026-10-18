import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    'live_check', Path(__file__).resolve().parents[1] / 'scripts/check_live_gateway.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class LiveCheckTests(unittest.TestCase):
    def test_partial_or_error_responses_are_not_success(self):
        for sample in ({'status': 502}, {'status': None}, {'status': 200, 'body': {}},
                       {'status': 200, 'body': {'router_meta': {'tier': 'sandbox'},
                        'choices': [{'message': {'content': 'ok'}}]}}):
            self.assertFalse(check.valid_benign(sample))
        self.assertTrue(check.valid_benign({'status': 200, 'body': {
            'router_meta': {'tier': 'full'}, 'choices': [{'message': {'content': 'ok'}}]}}))

    def test_http_failure_is_preserved(self):
        session = Mock()
        session.post.return_value.status_code = 503
        session.post.return_value.json.return_value = {'error': 'unavailable'}
        sample = check.send(session, 'http://localhost:5000', 'hello')
        self.assertEqual(sample['status'], 503)
        self.assertFalse(check.valid_benign(sample))
        self.assertEqual(session.post.call_args.kwargs['json']['max_tokens'], 8)

    def test_quantiles(self):
        self.assertIsNone(check.summarize([]))
        summary = check.summarize([4, 1, 3, 2])
        self.assertEqual(summary['count'], 4)
        self.assertEqual(summary['mean_ms'], 2.5)
        self.assertAlmostEqual(summary['p95_ms'], 3.85)
