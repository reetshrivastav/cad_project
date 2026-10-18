import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    'pilot', Path(__file__).resolve().parents[1] / 'scripts/benchmark_gpu_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotTests(unittest.TestCase):
    def test_metrics_preserve_labels_and_filter_histograms(self):
        rows = pilot.parse_metrics(
            '# HELP comment\nvllm:kv_cache_usage_perc{engine="0"} 0.25\n'
            'vllm:request_success_total{finished_reason="stop"} 2\n'
            'vllm:request_queue_time_seconds_bucket{le="1"} 4\n')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['value'], .25)
        self.assertIn('engine="0"', rows[0]['raw'])

    def test_only_gateway_quarantine_is_successful_block(self):
        blocked = {'kind': 'demand', 'status': 403,
                   'body': {'error': {'code': 'risk_quarantine'}}}
        self.assertTrue(pilot.expected_result('gateway', blocked))
        self.assertFalse(pilot.expected_result('direct', blocked))
        for code in (400, 500, 502, None):
            self.assertFalse(pilot.expected_result('gateway', blocked | {'status': code}))

    def test_generation_requires_actual_output_and_token_cap(self):
        row = {'kind': 'benign', 'status': 200, 'requested_max_tokens': 16,
               'body': {'choices': [{'message': {'content': 'hello'}}],
                        'usage': {'completion_tokens': 5}}}
        self.assertTrue(pilot.expected_result('direct', row))
        row['body']['usage']['completion_tokens'] = 17
        self.assertFalse(pilot.expected_result('direct', row))
        row['body']['usage']['completion_tokens'] = 0
        self.assertFalse(pilot.expected_result('direct', row))

    def test_pilot_records_both_arms_and_alternates_order(self):
        import contextlib
        import io
        import json
        import tempfile
        from unittest.mock import patch

        status = {'router_ready': True, 'vllm': True, 'target_ready': True,
                  'target_model': 'Qwen/Qwen2.5-3B-Instruct'}
        def get(url, **kwargs):
            response = Mock()
            response.json.return_value = status if url.endswith('/api/status') else {
                'data': [{'id': status['target_model']}]}
            return response

        def send(base, model, prompt, cap, kind, gate=None):
            blocked = '5000' in base and kind == 'demand'
            body = {'error': {'code': 'risk_quarantine'}} if blocked else {
                'choices': [{'message': {'content': 'ok'}}], 'usage': {'completion_tokens': cap}}
            return {'kind': kind, 'requested_max_tokens': cap, 'status': 403 if blocked else 200,
                    'body': body, 'http_ms': 1}

        sampler = Mock()
        sampler.samples = [{'metrics': [{'name': 'vllm:kv_cache_usage_perc', 'value': .1}]}]
        manager = Mock()
        manager.__enter__ = Mock(return_value=sampler)
        manager.__exit__ = Mock(return_value=False)
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / 'pilot.json')
            with patch.object(pilot.requests, 'get', side_effect=get), \
                 patch.object(pilot, 'collect_telemetry', return_value={}), \
                 patch.object(pilot, 'Sampler', return_value=manager), \
                 patch.object(pilot, 'send', side_effect=send), \
                 patch.object(pilot.subprocess, 'check_output', return_value='test-commit'), \
                 patch('sys.argv', ['pilot', '--output', output]), \
                 contextlib.redirect_stdout(io.StringIO()):
                pilot.main()
            result = json.loads(Path(output).read_text())
        self.assertTrue(result['all_expected_outcomes_passed'])
        self.assertEqual([t['arm'] for t in result['trials']], ['direct', 'gateway', 'gateway', 'direct'])
        self.assertEqual(result['summary']['gateway']['demand_quarantined'], 2)
        self.assertEqual(result['summary']['direct']['reported_completion_tokens'], 2 * (256 + 16))
