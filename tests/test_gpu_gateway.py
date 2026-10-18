"""CPU regression checks; no model downloads or real GPU inference."""
import unittest
from unittest.mock import Mock, patch
import pandas as pd
import requests
import app
import cache_pressure as pressure
from router import assign_tier


class PressureTests(unittest.TestCase):
    def test_labeled_metrics_and_multiple_engines(self):
        self.assertEqual(pressure.parse_pressure(
            '# HELP example\nvllm:kv_cache_usage_perc{engine="0"} 0.2\n'
            'vllm:kv_cache_usage_perc{engine="1"} 0.9'), 0.9)

    def test_invalid_metrics(self):
        for value in ('NaN', 'Inf', '-1', '1.1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                pressure.parse_pressure('vllm:kv_cache_usage_perc ' + value)
        with self.assertRaises(ValueError):
            pressure.parse_pressure('vllm:num_requests_waiting 0')

    def test_high_pressure_and_boundaries(self):
        risks = pd.Series([0.24, 0.25, 0.35, 0.65, 0.75])
        self.assertEqual(assign_tier(risks).tolist(),
                         ['full', 'full', 'sandbox', 'sandbox', 'quarantine'])
        self.assertEqual(assign_tier(risks, pressure.choose_thresholds(.9)).tolist(),
                         ['full', 'sandbox', 'sandbox', 'quarantine', 'quarantine'])
        self.assertEqual(pressure.choose_thresholds(.85), (.35, .75))

    def test_stale_telemetry_is_conservative(self):
        with patch.multiple(pressure, _started=True, _value=.1, _updated=1), \
             patch.object(pressure.time, 'monotonic', return_value=10):
            state = pressure.snapshot()
        self.assertTrue(state['stale'])
        self.assertEqual(state['quarantine_threshold'], .65)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_forwarder_preserves_conversation_and_finish_reason(self):
        response = Mock()
        response.json.return_value = {
            'choices': [{'message': {'content': 'answer'}, 'finish_reason': 'length'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
        messages = [{'role': 'system', 'content': 'Be concise'},
                    {'role': 'user', 'content': 'Hello'}]
        with patch.object(app.http_req, 'post', return_value=response) as post:
            result = app.call_vllm(messages=messages, max_tokens=5)
        self.assertEqual(post.call_args.kwargs['json']['messages'], messages)
        self.assertTrue(post.call_args.args[0].endswith('/v1/chat/completions'))
        self.assertEqual(result['finish_reason'], 'length')

    def test_forwarder_timeout(self):
        with patch.object(app.http_req, 'post', side_effect=requests.Timeout):
            self.assertEqual(app.call_vllm('hello')['error'], 'vllm_request_timeout')

    def route(self, risk):
        classifier = Mock()
        classifier.risk_scores.return_value = (pd.Series([risk]), None, None)
        return patch.object(app, '_classifier', classifier)

    def test_quarantine_does_not_call_backend(self):
        policy = {'sandbox_threshold': .25, 'quarantine_threshold': .65}
        with self.route(.7), patch.object(app, 'pressure_snapshot', return_value=policy), \
             patch.object(app, 'extract_real_features', return_value={c: 0 for c in app.FEATURE_COLUMNS}), \
             patch.object(app, 'call_vllm') as forward:
            response = self.client.post('/v1/chat/completions', json={
                'messages': [{'role': 'user', 'content': 'test'}]})
        self.assertEqual(response.status_code, 403)
        forward.assert_not_called()

    def test_sandbox_caps_and_reports_policy(self):
        policy = {'sandbox_threshold': .25, 'quarantine_threshold': .65}
        features = {c: 0 for c in app.FEATURE_COLUMNS}
        features['_extract_ms'] = 1
        with self.route(.4), patch.object(app, 'pressure_snapshot', return_value=policy), \
             patch.object(app, 'extract_real_features', return_value=features), \
             patch.object(app, 'call_vllm', return_value={'ok': True, 'text': 'ok'}) as forward:
            response = self.client.post('/v1/chat/completions', json={
                'messages': [{'role': 'user', 'content': 'test'}], 'max_tokens': 1024})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(forward.call_args.kwargs['max_tokens'], 256)
        self.assertEqual(forward.call_args.kwargs['timeout'], 5)
        self.assertEqual(response.json['router_meta']['thresholds']['quarantine'], .65)


if __name__ == '__main__':
    unittest.main()
