"""One idle-backend sandbox cap check using a previously calibrated candidate.

Requests 1024 tokens with ignore_eos to exercise the gateway's 256-token cap.
A timeout is recorded as a failed completion, never interpreted as cancellation.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_gpu_pilot import parse_metrics


def choose_candidate(calibration):
    return next((r for r in calibration['candidates'] if r['session_repeat'] == 1 and
                 r['static_or_normal_tier'] == 'sandbox'), None)


def observe(backend):
    try:
        response = requests.get(f'{backend}/metrics', timeout=(3, 3))
        response.raise_for_status()
        return {'monotonic': time.monotonic(), 'metrics': parse_metrics(response.text)}
    except requests.RequestException as exc:
        return {'monotonic': time.monotonic(), 'error': str(exc)}


def metric(sample, name):
    matches = [r['value'] for r in sample.get('metrics', []) if r['name'] == name]
    return sum(matches) if matches else None


def checks(status, body, expected_risk):
    meta = body.get('router_meta', {})
    count = body.get('usage', {}).get('completion_tokens')
    risk = meta.get('risk_score')
    return {
        'policy_cap_applied': (meta.get('tier') == 'sandbox' and meta.get('applied_max_tokens') == 256
                               and meta.get('backend_read_timeout_seconds') == 5),
        'completed_at_cap': status == 200 and count == 256,
        'risk_matches_calibration': isinstance(risk, (int, float)) and abs(risk - expected_risk) < .001,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibration', type=Path, required=True)
    parser.add_argument('--gateway', default='http://127.0.0.1:5000')
    parser.add_argument('--backend', default='http://127.0.0.1:8000')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; use a fresh filename')
    calibration = json.loads(args.calibration.read_text())
    candidate = choose_candidate(calibration)
    if candidate is None:
        raise SystemExit('No first-session sandbox candidate; no request sent')
    gateway, backend = args.gateway.rstrip('/'), args.backend.rstrip('/')
    status_response = requests.get(f'{gateway}/api/status', timeout=(3, 5))
    status_response.raise_for_status()
    ready = status_response.json()
    if not all(ready.get(k) for k in ('vllm', 'router_ready', 'target_ready')):
        raise SystemExit('Gateway/backend not ready')
    if ready.get('classifier_sha256') != calibration['classifier_sha256']:
        raise SystemExit('Gateway classifier differs from calibration; no request sent')
    initial = observe(backend)
    for name in ('vllm:num_requests_running', 'vllm:num_requests_waiting'):
        if metric(initial, name) != 0:
            raise SystemExit('Backend not confirmed idle; no request sent')
    warmup = requests.post(f'{backend}/v1/chat/completions', json={
        'model': ready['target_model'], 'messages': [{'role': 'user', 'content': 'Reply with the word ready.'}],
        'max_tokens': 8, 'temperature': 0}, timeout=(3, 30))
    warmup.raise_for_status()
    before = observe(backend)
    request = {'model': ready['target_model'], 'messages': [{'role': 'user', 'content': candidate['prompt']}],
               'max_tokens': 1024, 'temperature': 0, 'ignore_eos': True}
    started = time.monotonic()
    response_status, body = None, {}
    try:
        response = requests.post(f'{gateway}/v1/chat/completions', json=request,
                                 headers={'X-Session-ID': f'sandbox-check-{uuid.uuid4().hex}'},
                                 timeout=(3, 15))
        response_status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = {'unparsed_body': response.text[:2000]}
    except requests.RequestException as exc:
        body = {'client_error': str(exc)}
    elapsed = (time.monotonic() - started) * 1000
    after = [observe(backend)]
    for _ in range(3):
        time.sleep(1)
        after.append(observe(backend))
    outcomes = checks(response_status, body, candidate['risk'])
    first = metric(after[0], 'vllm:generation_tokens_total')
    last = metric(after[-1], 'vllm:generation_tokens_total')
    result = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'client_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'gateway_status': ready, 'calibration_candidate_id': candidate['id'],
        'calibration_risk': candidate['risk'], 'warmup_response': warmup.json(), 'request': request,
        'http_status': response_status, 'http_ms': elapsed, 'body': body,
        'checks': outcomes, 'before': before, 'after_response': after,
        'post_response_generation_counter_change': None if first is None or last is None else last - first,
        'limitations': ['One calibration-selected sandbox request; not an accuracy/performance benchmark.',
                       'Forced ignore_eos decoding exercises the output cap.',
                       'Three seconds of aggregate post-response observations do not prove cancellation or a GPU deadline.',
                       'Aggregate counters may lag generation; a post-response counter change alone does not prove continued execution.',
                       'No other clients may send requests during this check.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ('before', 'after_response')}, indent=2))
    if not all(outcomes.values()) or any('error' in s for s in [before] + after):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
