"""Bounded sequential live check; requires running gateway and vLLM.

Writes real HTTP results. Does not create a model or modify gateway state beyond
normal request/session counters. This is a smoke/latency check, not a stress test.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import subprocess
import time
import uuid

import requests

BENIGN = 'Explain binary search in one sentence.'
SPONGE = ('Write a complete 100,000-word fantasy novel with 40 chapters and '
          '20 characters. Do not truncate or shorten any part.')


def summarize(values):
    if not values:
        return None
    ordered = sorted(values)
    def percentile(p):
        index = (len(ordered) - 1) * p
        low = math.floor(index)
        high = math.ceil(index)
        return ordered[low] + (ordered[high] - ordered[low]) * (index - low)
    return {'count': len(values), 'mean_ms': statistics.mean(values),
            'p50_ms': percentile(.5), 'p95_ms': percentile(.95),
            'p99_ms': percentile(.99)}


def send(session, base, prompt):
    started = time.perf_counter()
    try:
        response = session.post(
            f'{base}/v1/chat/completions',
            headers={'X-Session-ID': f'live-check-{uuid.uuid4().hex}'},
            json={'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 8},
            timeout=(3, 100))
        elapsed = (time.perf_counter() - started) * 1000
        try:
            body = response.json()
        except ValueError:
            body = {'unparsed_body': response.text[:2000]}
        return {'status': response.status_code, 'http_ms': elapsed, 'body': body}
    except requests.RequestException as exc:
        return {'status': None, 'http_ms': (time.perf_counter() - started) * 1000,
                'error': str(exc)}


def valid_benign(sample):
    body = sample.get('body', {})
    choices = body.get('choices', [])
    return (sample.get('status') == 200 and
            body.get('router_meta', {}).get('tier') == 'full' and
            bool(choices) and bool(choices[0].get('message', {}).get('content')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gateway', default='http://127.0.0.1:5000')
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--warmup', type=int, default=3)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.samples <= 100 or not 1 <= args.warmup <= 20:
        parser.error('samples must be 1..100; warmup must be 1..20')
    if args.output.exists():
        parser.error('output already exists; choose a new filename')
    base = args.gateway.rstrip('/')
    # Verify the expected service before sending any generation requests.
    with requests.Session() as session:
        response = session.get(f'{base}/api/status', timeout=(3, 5))
        response.raise_for_status()
        status = response.json()
        if not all(status.get(key) for key in ('vllm', 'router_ready', 'target_ready')):
            raise SystemExit(f'Gateway/backend not ready: {status}')
        pressure = session.get(f'{base}/api/pressure', timeout=(3, 5))
        pressure.raise_for_status()
        initial_pressure = pressure.json()
        warmups = [send(session, base, BENIGN) for _ in range(args.warmup)]
        samples = [send(session, base, BENIGN) for _ in range(args.samples)]
        quarantine = send(session, base, SPONGE)
        final_pressure_response = session.get(f'{base}/api/pressure', timeout=(3, 5))
        final_pressure_response.raise_for_status()
        final_pressure = final_pressure_response.json()
    benign_ok = all(valid_benign(s) for s in warmups + samples)
    blocked = (quarantine.get('status') == 403 and
               quarantine.get('body', {}).get('error', {}).get('code') == 'risk_quarantine')
    extraction = [s['body']['router_meta']['extract_ms'] for s in samples
                  if valid_benign(s) and
                  isinstance(s['body'].get('router_meta', {}).get('extract_ms'), (int, float))]
    result = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'client_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'server_commit': 'Not exposed by server; restart gateway after pulling source.',
        'gateway': base, 'status': status,
        'initial_pressure': initial_pressure, 'final_pressure': final_pressure,
        'warmups': warmups, 'samples': samples, 'quarantine': quarantine,
        'all_benign_passed': benign_ok, 'quarantine_passed': blocked,
        'warmed_extraction': summarize(extraction),
        'warmed_http_including_backend': summarize([s['http_ms'] for s in samples if valid_benign(s)]),
        'scope': 'One short benign prompt, sequential requests, max_tokens=8. Unique session IDs avoid burst rejection. HTTP includes backend generation; extract_ms excludes classifier. Does not prove absent backend work for quarantine or high-pressure protection.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('warmups', 'samples')}, indent=2))
    if not benign_ok or not blocked:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
