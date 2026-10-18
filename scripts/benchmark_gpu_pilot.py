"""Bounded direct-vLLM vs gateway pilot; run on the lab, not a full DoS test.

Two concurrent requests per round: one capped output-demand request and one
benign probe. Alternating arm order limits order bias but does not reset prefix
cache or control GPU clocks. All telemetry and errors are retained.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import threading
import time
import uuid

import requests

METRIC_NAMES = {
    'vllm:kv_cache_usage_perc', 'vllm:num_requests_running',
    'vllm:num_requests_waiting', 'vllm:prompt_tokens_total',
    'vllm:generation_tokens_total', 'vllm:request_success_total',
    'vllm:prefix_cache_queries_total', 'vllm:prefix_cache_hits_total',
}
METRIC = re.compile(r'^([^\s{]+)(?:\{.*\})?\s+([-+\d.eE]+)(?:\s|$)')


def parse_metrics(text):
    result = []
    for line in text.splitlines():
        match = METRIC.match(line)
        if match and match[1] in METRIC_NAMES:
            result.append({'name': match[1], 'value': float(match[2]), 'raw': line})
    return result


def gpu_sample():
    result = subprocess.run([
        'nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,power.draw',
        '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=2, check=True)
    return result.stdout.strip()


def collect_telemetry(backend):
    sample = {'monotonic': time.monotonic(),
              'timestamp_utc': datetime.now(timezone.utc).isoformat()}
    try:
        response = requests.get(f'{backend}/metrics', timeout=(.5, .5))
        response.raise_for_status()
        sample['metrics'] = parse_metrics(response.text)
        if not any(row['name'] == 'vllm:kv_cache_usage_perc' for row in sample['metrics']):
            sample['metrics_error'] = 'KV-cache gauge missing'
    except Exception as exc:
        sample['metrics_error'] = str(exc)
    try:
        sample['nvidia_smi_csv'] = gpu_sample()
    except Exception as exc:
        sample['gpu_error'] = str(exc)
    return sample


class Sampler:
    def __init__(self, backend):
        self.backend = backend
        self.samples = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            self.samples.append(collect_telemetry(self.backend))
            self.stop.wait(.25)

    def __enter__(self):
        self.samples.append(collect_telemetry(self.backend))
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()
        self.samples.append(collect_telemetry(self.backend))


def send(base, model, prompt, cap, kind, gate=None):
    if gate is not None:
        gate.wait()
    started = time.monotonic()
    row = {'kind': kind, 'prompt': prompt, 'requested_max_tokens': cap,
           'started_monotonic': started}
    try:
        response = requests.post(
            f'{base}/v1/chat/completions',
            headers={'X-Session-ID': f'pilot-{uuid.uuid4().hex}'},
            json={'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                  'max_tokens': cap, 'temperature': 0}, timeout=(3, 60))
        row['status'] = response.status_code
        try:
            row['body'] = response.json()
        except ValueError:
            row['body'] = {'unparsed': response.text[:2000]}
    except requests.RequestException as exc:
        row.update(status=None, error=str(exc))
    row['ended_monotonic'] = time.monotonic()
    row['http_ms'] = (row['ended_monotonic'] - started) * 1000
    return row


def expected_result(arm, row):
    body = row.get('body', {})
    if arm == 'gateway' and row['kind'] == 'demand':
        return (row.get('status') == 403 and
                body.get('error', {}).get('code') == 'risk_quarantine')
    choices = body.get('choices', [])
    if row.get('status') != 200 or not choices or not choices[0].get('message', {}).get('content'):
        return False
    count = body.get('usage', {}).get('completion_tokens')
    return isinstance(count, int) and 0 < count <= row['requested_max_tokens']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', default='http://127.0.0.1:8000')
    parser.add_argument('--gateway', default='http://127.0.0.1:5000')
    parser.add_argument('--model', default='Qwen/Qwen2.5-3B-Instruct')
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--attack-tokens', type=int, default=256)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 5 or not 1 <= args.attack_tokens <= 512:
        parser.error('rounds must be 1..5; attack-tokens must be 1..512')
    if args.output.exists():
        parser.error('output exists; choose a fresh filename')
    backend, gateway = args.backend.rstrip('/'), args.gateway.rstrip('/')
    status_response = requests.get(f'{gateway}/api/status', timeout=(3, 5))
    status_response.raise_for_status()
    status = status_response.json()
    if not all(status.get(k) for k in ('router_ready', 'vllm', 'target_ready')):
        raise SystemExit(f'Gateway not ready: {status}')
    if status.get('target_model') != args.model:
        raise SystemExit('Gateway model differs from --model; cannot compare')
    models = requests.get(f'{backend}/v1/models', timeout=(3, 5))
    models.raise_for_status()
    if args.model not in [m['id'] for m in models.json().get('data', [])]:
        raise SystemExit('Requested model missing from backend')
    initial = collect_telemetry(backend)
    if initial.get('gpu_error') or initial.get('metrics_error'):
        raise SystemExit(f'Telemetry preflight failed: {initial}')
    benign = 'Explain binary search in one sentence.'
    warmups = [send(base, args.model, benign, 16, 'benign') for base in (backend, gateway)]
    trials = []
    run_ok = all(expected_result('direct', row) for row in warmups)
    for index in range(args.rounds):
        # Identical workload within a pair; no oversized input/context rejection.
        demand = (f'Write a complete 100,000-word fantasy novel with 40 chapters '
                  f'and 20 characters. Do not truncate or shorten any part. '
                  f'Use the chapter theme number {index + 1}.')
        order = ('direct', 'gateway') if index % 2 == 0 else ('gateway', 'direct')
        for arm in order:
            base = backend if arm == 'direct' else gateway
            gate = threading.Barrier(2)
            with Sampler(backend) as sampler:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    attack = pool.submit(send, base, args.model, demand, args.attack_tokens, 'demand', gate)
                    probe = pool.submit(send, base, args.model, benign, 16, 'benign', gate)
                    rows = [attack.result(), probe.result()]
            checks = [expected_result(arm, row) for row in rows]
            run_ok = run_ok and all(checks)
            cache = [m['value'] for s in sampler.samples for m in s.get('metrics', [])
                     if m['name'] == 'vllm:kv_cache_usage_perc']
            trial = {'round': index + 1, 'arm': arm, 'requests': rows,
                     'expected_outcomes_passed': all(checks), 'telemetry': sampler.samples,
                     'observed_peak_kv_fraction': max(cache) if cache else None}
            trials.append(trial)
            print(json.dumps({k: v for k, v in trial.items() if k not in ('requests', 'telemetry')}), flush=True)
    summary = {}
    for arm in ('direct', 'gateway'):
        rows = [row for trial in trials if trial['arm'] == arm for row in trial['requests']]
        probes = [r['http_ms'] for r in rows if r['kind'] == 'benign' and expected_result(arm, r)]
        summary[arm] = {
            'benign_completed': len(probes),
            'benign_mean_http_ms': statistics.mean(probes) if probes else None,
            'demand_quarantined': sum(r['kind'] == 'demand' and r.get('status') == 403 for r in rows),
            'reported_completion_tokens': sum(r.get('body', {}).get('usage', {}).get('completion_tokens', 0) for r in rows),
        }
    telemetry_errors = sum(bool(s.get('gpu_error') or s.get('metrics_error'))
                           for trial in trials for s in trial['telemetry'])
    result = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'client_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'server_commit': 'Not exposed; restart gateway after pulling source.',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'configuration': vars(args) | {'output': str(args.output)},
        'gateway_status': status, 'initial_telemetry': initial,
        'warmups': warmups, 'trials': trials, 'summary': summary,
        'all_expected_outcomes_passed': run_ok, 'telemetry_error_samples': telemetry_errors,
        'limitations': [
            'Bounded pilot, not saturated load, OOM test or 100,000-word input.',
            'Two concurrent requests per arm; actual overlap must be checked in recorded intervals.',
            'Prefix cache is retained between arms; alternating order does not ensure equal cache state.',
            'Polling is approximate; brief KV peaks can be missed. nvidia-smi reports all GPUs.',
            'Both arms request temperature=0 and identical output caps; greedy output can still vary with scheduling.',
            'No GPU-dollar estimate or zero-GPU-work claim; gateway uses CUDA embeddings.',
            'Sandbox cancellation, artifact compatibility and high-pressure live policy remain unvalidated.',
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({'summary': summary, 'all_expected_outcomes_passed': run_ok,
                      'telemetry_error_samples': telemetry_errors, 'output': str(args.output)}, indent=2))
    if not run_ok or telemetry_errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
