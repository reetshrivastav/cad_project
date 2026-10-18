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

        def send(base, model, prompt, cap, kind, gate=None, delay=0, request_timeout=60, ignore_eos=False):
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

    def run_burst(self, peak, fail_benign=False):
        import contextlib
        import io
        import json
        import tempfile
        from unittest.mock import patch
        calls = []
        status = {'router_ready': True, 'vllm': True, 'target_ready': True,
                  'target_model': 'Qwen/Qwen2.5-3B-Instruct'}
        def get(url, **kwargs):
            response = Mock()
            response.json.return_value = status if url.endswith('/api/status') else {
                'data': [{'id': status['target_model']}]}
            return response
        def send(base, model, prompt, cap, kind, gate=None, delay=0, request_timeout=60, ignore_eos=False):
            if gate:
                gate.wait(timeout=5)
            calls.append((base, cap, kind, delay, ignore_eos))
            if fail_benign and kind == 'benign' and gate is not None:
                return {'kind': kind, 'status': 503, 'http_ms': 1, 'requested_max_tokens': cap, 'body': {'error': 'failed'}}
            blocked = '5000' in base and kind == 'demand'
            return {'kind': kind, 'status': 403 if blocked else 200,
                    'requested_max_tokens': cap, 'http_ms': 1,
                    'body': {'error': {'code': 'risk_quarantine'}} if blocked else {
                        'choices': [{'message': {'content': 'ok'}}], 'usage': {'completion_tokens': cap}}}
        sampler = Mock()
        sampler.samples = [{'metrics': [{'name': 'vllm:kv_cache_usage_perc', 'value': peak}],
                            'gateway_policy': {'policy': 'high_pressure' if peak > .85 else 'normal'}}]
        manager = Mock()
        manager.__enter__ = Mock(return_value=sampler)
        manager.__exit__ = Mock(return_value=False)
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / 'burst.json')
            with patch.object(pilot.requests, 'get', side_effect=get), \
                 patch.object(pilot, 'collect_telemetry', return_value={}), \
                 patch.object(pilot, 'Sampler', return_value=manager), \
                 patch.object(pilot, 'send', side_effect=send), \
                 patch.object(pilot.subprocess, 'check_output', return_value='test-commit'), \
                 patch('sys.argv', ['pilot', '--output', output, '--rounds', '1',
                                    '--demands-per-round', '3', '--benign-per-round', '2',
                                    '--probe-interval', '1', '--attack-tokens', '1024',
                                    '--ignore-eos', '--target-pressure', '.85']), \
                 contextlib.redirect_stdout(io.StringIO()):
                if peak < .85 or fail_benign:
                    with self.assertRaises(SystemExit):
                        pilot.main()
                else:
                    pilot.main()
            result = json.loads(Path(output).read_text())
        return result, calls

    def test_multi_request_burst_and_staggered_probes(self):
        result, calls = self.run_burst(.9)
        self.assertTrue(result['target_pressure_reached'])
        self.assertEqual(result['summary']['direct']['reported_completion_tokens'], 3 * 1024 + 2 * 16)
        self.assertEqual(result['summary']['gateway']['demand_quarantined'], 3)
        self.assertEqual(len(result['trials'][0]['requests']), 5)
        demands = [c for c in calls if c[2] == 'demand']
        self.assertTrue(all(c[4] for c in demands))
        self.assertTrue(any(c[3] == 1 for c in calls if c[2] == 'benign'))

    def test_missing_pressure_target_keeps_evidence_and_fails(self):
        result, _ = self.run_burst(.1)
        self.assertFalse(result['target_pressure_reached'])
        self.assertTrue(result['all_expected_outcomes_passed'])

    def test_unexpected_outcome_stops_following_arms_and_preserves_data(self):
        result, _ = self.run_burst(.9, fail_benign=True)
        self.assertTrue(result['aborted_after_unexpected_outcome'])
        self.assertEqual(len(result['trials']), 1)
        self.assertFalse(result['all_expected_outcomes_passed'])
