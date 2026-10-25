"""Analyze recorded multi-request GPU trials offline; no server requests.

Requires matching native-model metadata. Preserves failed requests in the output
and reports no p99 below 100 successful benign samples.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_gpu_pilot import counter_delta, metric_values


def validate_metadata(data, metadata):
    expected = metadata['artifact_sha256']['classifier.joblib']
    observed = data['gateway_status'].get('classifier_sha256')
    if observed != expected:
        raise ValueError('Gateway classifier hash does not match supplied model metadata')


def summarize(data, metadata):
    validate_metadata(data, metadata)
    trials = []
    for trial in data['trials']:
        rows = trial['requests']
        samples = trial['telemetry']
        benign = [r for r in rows if r['kind'] == 'benign']
        demands = [r for r in rows if r['kind'] == 'demand']
        successful = [r for r in benign if r.get('status') == 200 and
                      r.get('body', {}).get('choices')]
        generated = sum(r.get('body', {}).get('usage', {}).get('completion_tokens', 0) for r in rows)
        prompt = sum(r.get('body', {}).get('usage', {}).get('prompt_tokens', 0) for r in rows)
        generation_delta = counter_delta(samples, 'vllm:generation_tokens_total')
        prompt_delta = counter_delta(samples, 'vllm:prompt_tokens_total')
        success_delta = counter_delta(samples, 'vllm:request_success_total')
        times = [r['http_ms'] for r in successful]
        kv = metric_values(samples, 'vllm:kv_cache_usage_perc')
        memory = []
        for sample in samples:
            for fields in csv.reader(io.StringIO(sample.get('nvidia_smi_csv', ''))):
                if len(fields) == 6 and fields[0].strip() == '0':
                    memory.append(float(fields[2]))
        trial_start = min(r['started_monotonic'] for r in rows)
        trial_end = max(r['ended_monotonic'] for r in rows)
        request_policies = [r.get('body', {}).get('router_meta', {}).get('pressure_policy', {}).get('policy')
                            for r in rows]
        trials.append({
            'round': trial['round'], 'arm': trial['arm'],
            'demand_count': len(demands), 'benign_count': len(benign),
            'benign_completed': len(successful), 'benign_failed': len(benign) - len(successful),
            'demands_quarantined': sum(r.get('status') == 403 and
                                      r.get('body', {}).get('error', {}).get('code') == 'risk_quarantine'
                                      for r in demands),
            'benign_mean_http_ms': statistics.mean(times) if times else None,
            'benign_min_http_ms': min(times, default=None),
            'benign_max_http_ms': max(times, default=None),
            'benign_p99_http_ms': sorted(times)[int((len(times)-1)*.99)] if len(times) >= 100 else None,
            'request_wall_span_seconds': trial_end - trial_start,
            'backend_prompt_tokens_delta': prompt_delta,
            'backend_generation_tokens_delta': generation_delta,
            'backend_successful_requests_delta': success_delta,
            'http_reported_prompt_tokens': prompt, 'http_reported_completion_tokens': generated,
            'counter_usage_matches': (prompt_delta == prompt and generation_delta == generated and
                                      success_delta == sum(r.get('status') == 200 for r in rows)),
            'observed_peak_kv_fraction': max(kv, default=None),
            'peak_waiting': max(metric_values(samples, 'vllm:num_requests_waiting'), default=None),
            'peak_running': max(metric_values(samples, 'vllm:num_requests_running'), default=None),
            'gpu0_min_memory_mib': min(memory, default=None),
            'gpu0_max_memory_mib': max(memory, default=None),
            'high_pressure_policy_samples': sum(s.get('gateway_policy', {}).get('policy') == 'high_pressure'
                                                 for s in samples),
            'request_policy_counts': {p: request_policies.count(p) for p in set(request_policies) if p},
            'telemetry_samples': len(samples),
        })
    return {'classifier_sha256': data['gateway_status']['classifier_sha256'],
            'metadata_accuracy_scope': metadata['accuracy_scope'],
            'training_set_accuracy': metadata['accuracy'],
            'trials': trials,
            'scope': 'One calibration run; no p99 below 100 successful probes; no causal static-vs-adaptive conclusion.'}


def render(data, directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    trace_rows = []
    for trial in data['trials']:
        color = '#c75b39' if trial['arm'] == 'direct' else '#227e75'
        mode = data.get("gateway_status", {}).get("routing_mode", "unknown")
        label = f"R{trial['round']} {trial['arm']}" + (f" ({mode})" if trial["arm"] == "gateway" else "")
        start = min(r['started_monotonic'] for r in trial['requests'])
        times, kvs, queues, gpu_times, memories = [], [], [], [], []
        for sample in trial['telemetry']:
            elapsed = sample['monotonic'] - start
            kv = metric_values([sample], 'vllm:kv_cache_usage_perc')
            queue = metric_values([sample], 'vllm:num_requests_waiting')
            if kv and queue:
                times.append(elapsed); kvs.append(kv[0] * 100); queues.append(queue[0])
            memory = None
            for fields in csv.reader(io.StringIO(sample.get('nvidia_smi_csv', ''))):
                if len(fields) == 6 and fields[0].strip() == '0':
                    memory = float(fields[2]); gpu_times.append(elapsed); memories.append(memory)
            trace_rows.append({'round': trial['round'], 'arm': trial['arm'], 'relative_seconds': elapsed,
                               'kv_fraction': kv[0] if kv else None, 'waiting': queue[0] if queue else None,
                               'gpu0_memory_mib': memory, 'policy': sample.get('gateway_policy', {}).get('policy')})
        axes[0, 0].plot(times, kvs, label=label, color=color)
        axes[0, 1].step(times, queues, where='post', label=label, color=color)
        benign = [r for r in trial['requests'] if r['kind'] == 'benign' and r.get('status') == 200]
        axes[1, 0].plot([r['started_monotonic'] - start for r in benign],
                        [r['http_ms'] / 1000 for r in benign], 'o-', label=label, color=color)
        axes[1, 1].plot(gpu_times, memories, label=label, color=color)
    for ax, title, xlabel, ylabel in [
        (axes[0, 0], 'Sampled KV-cache occupancy', 'Seconds relative to each trial start', '% of KV blocks'),
        (axes[0, 1], 'Backend waiting requests', 'Seconds relative to each trial start', 'Requests'),
        (axes[1, 0], 'Benign response time (8 probes per arm)', 'Probe start relative to its trial (s)', 'Seconds including generation'),
        (axes[1, 1], 'Device allocation (nonzero axis baseline)', 'Seconds relative to each trial start', 'GPU 0 memory used (MiB)'),
    ]:
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.grid(alpha=.2); ax.legend()
    axes[0, 0].axhline(85, color='gray', linestyle='--', linewidth=1)
    direct_present = any(trial["arm"] == "direct" for trial in data["trials"])
    subtitle = ('Direct/gateway calibration; controlled resource pressure' if direct_present else
                f'Gateway-only {data.get("gateway_status", {}).get("routing_mode", "unknown")} control')
    config = data["configuration"]
    fig.suptitle(f'RTX A4000: {config.get("demands_per_round", 1)} capped demands + '
                 f'{config.get("benign_per_round", 1)} probes per trial\n'
                 f'{subtitle}; not default-cache or P99 evidence', fontsize=11)
    fig.savefig(directory / 'burst_comparison.png', dpi=200)
    fig.savefig(directory / 'burst_comparison.svg')
    plt.close(fig)
    with (directory / 'telemetry_trace.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trace_rows[0]))
        writer.writeheader(); writer.writerows(trace_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('output directory exists; choose a fresh directory')
    raw, raw_meta = args.input.read_bytes(), args.metadata.read_bytes()
    data, metadata = json.loads(raw), json.loads(raw_meta)
    result = summarize(data, metadata)
    result.update(source_sha256=hashlib.sha256(raw).hexdigest(),
                  metadata_sha256=hashlib.sha256(raw_meta).hexdigest(),
                  source_client_commit=data['client_commit'])
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'derived_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    with (args.output_dir / 'trial_metrics.csv').open('w') as handle:
        flat = [{k: v for k, v in row.items() if k != 'request_policy_counts'} for row in result['trials']]
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader(); writer.writerows(flat)
    render(data, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
