"""Offline analysis of all nine prespecified GPU replication runs."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_gpu_burst import summarize
from analyze_gpu_pilot import metric_values
from benchmark_gpu_pilot import expected_result

CONDITIONS = ('direct', 'static', 'adaptive')
ORDER = ('b1_direct', 'b1_static', 'b1_adaptive', 'b2_static', 'b2_adaptive',
         'b2_direct', 'b3_adaptive', 'b3_direct', 'b3_static')


def analyze(records, metadata):
    if set(records) != set(ORDER):
        raise ValueError('Expected exactly the nine scheduled run IDs')
    rows, configs, hashes = [], [], set()
    for run_id in ORDER:
        data = records[run_id]
        condition = run_id.split('_')[1]
        arm = 'direct' if condition == 'direct' else 'gateway'
        mode = 'adaptive' if condition == 'adaptive' else 'static'
        config = data['configuration']
        if (data['gateway_status']['routing_mode'] != mode or config['arms'] != [arm]
                or config['require_routing_mode'] != mode or len(data['trials']) != 1
                or data['trials'][0]['arm'] != arm):
            raise ValueError(f'{run_id}: condition/mode mismatch')
        required = dict(rounds=1, attack_tokens=1792, demands_per_round=8,
                        benign_per_round=8, probe_interval=3, request_timeout=240,
                        ignore_eos=True, target_pressure=.85 if arm == 'direct' else None)
        if any(config.get(k) != v for k, v in required.items()):
            raise ValueError(f'{run_id}: workload differs from protocol')
        configs.append({k: v for k, v in config.items() if k not in
                        ('arms', 'require_routing_mode', 'target_pressure', 'output')})
        hashes.add(data['script_sha256'])
        row = summarize(data, metadata)['trials'][0]
        trial = data['trials'][0]
        requests = trial['requests']
        if row['demand_count'] != 8 or row['benign_count'] != 8:
            raise ValueError(f'{run_id}: missing requests')
        row.update(run_id=run_id, condition=condition, timestamp_utc=data['timestamp_utc'],
                   client_commit=data['client_commit'],
                   verified_expected_outcomes=all(expected_result(arm, r) for r in requests),
                   verified_warmups=all(expected_result('direct', r) for r in data['warmups']),
                   telemetry_error_samples=sum(bool(s.get('gpu_error') or s.get('metrics_error')
                       or s.get('gateway_policy_error')) for s in trial['telemetry']),
                   verified_target_reached=(row['observed_peak_kv_fraction'] >= .85
                       if arm == 'direct' and row['observed_peak_kv_fraction'] is not None else None))
        initial = data['initial_telemetry']
        row['initial_idle_zero_token_counters'] = all(
            metric_values([initial], name) == [0] for name in (
                'vllm:num_requests_running', 'vllm:num_requests_waiting',
                'vllm:prompt_tokens_total', 'vllm:generation_tokens_total'))
        cache = initial.get('cache_config_lines', [])
        row['recorded_cache_config_matches'] = bool(cache) and all(
            all(part in line for part in ('kv_cache_memory_bytes="268435456"',
                'kv_cache_size_tokens="7280"', 'num_gpu_blocks="455"',
                'enable_prefix_caching="True"')) for line in cache)
        events = [(r['started_monotonic'], 1) for r in requests]
        events += [(r['ended_monotonic'], -1) for r in requests]
        active = peak = 0
        for _, delta in sorted(events):
            active += delta
            peak = max(peak, active)
        row['peak_overlapping_client_intervals'] = peak
        rows.append(row)
    if len(hashes) != 1 or any(c != configs[0] for c in configs):
        raise ValueError('Benchmark code hashes or workload configurations differ')
    observed_order = sorted(records, key=lambda key: datetime.fromisoformat(records[key]['timestamp_utc']))
    conditions = {}
    for condition in CONDITIONS:
        group = [r for r in rows if r['condition'] == condition]
        means = [r['benign_mean_http_ms'] for r in group if r['benign_mean_http_ms'] is not None]
        conditions[condition] = {
            'runs': len(group), 'mean_of_run_means_http_ms': statistics.mean(means) if means else None,
            'min_run_mean_http_ms': min(means, default=None),
            'max_run_mean_http_ms': max(means, default=None),
            **{field: sum(r[field] for r in group) for field in (
                'benign_completed', 'benign_failed', 'demands_quarantined',
                'backend_prompt_tokens_delta', 'backend_generation_tokens_delta')},
            'benign_p99_http_ms': None,
        }
    return {'runs': rows, 'conditions': conditions, 'observed_order': observed_order,
            'order_matches_protocol': observed_order == list(ORDER),
            'benchmark_sha256': next(iter(hashes)),
            'all_counters_reconcile': all(r['counter_usage_matches'] for r in rows),
            'scope': 'Three repetitions per condition; 24 benign probes each; no P99, causal adaptation, or dollar estimate.'}


def render(result, directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout='constrained')
    panels = [('benign_mean_http_ms', 'Mean benign HTTP latency', 'ms (log scale)'),
              ('observed_peak_kv_fraction', 'Sampled peak KV occupancy', '% of configured KV blocks'),
              ('peak_waiting', 'Sampled peak waiting queue', 'requests')]
    colors = ('#bb4c37', '#407aa3', '#268479')
    for ax, (field, title, unit) in zip(axes, panels):
        for i, (condition, color) in enumerate(zip(CONDITIONS, colors)):
            group = [r for r in result['runs'] if r['condition'] == condition]
            values = [r[field] * (100 if field == 'observed_peak_kv_fraction' else 1) for r in group]
            ax.scatter([i-.08, i, i+.08], values, color=color, s=45)
        ax.set_xticks(range(3), CONDITIONS)
        ax.set(title=title, ylabel=unit)
        ax.grid(axis='y', alpha=.2)
    axes[0].set_yscale('log')
    fig.suptitle('RTX A4000: three runs per condition, constrained 256 MiB KV pool\n'
                 'Each dot is one run; capped forced decoding; no P99 estimate', fontsize=11)
    for suffix in ('png', 'svg'):
        fig.savefig(directory / f'replication_comparison.{suffix}', dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('output directory exists; choose a new path')
    records = {key: json.loads((args.input_dir / f'{key}.json').read_text()) for key in ORDER}
    manifest = json.loads((args.input_dir / 'source_manifest.json').read_text())
    for key in ORDER:
        name = f'{key}.json'
        if hashlib.sha256((args.input_dir / name).read_bytes()).hexdigest() != manifest['files_sha256'][name]:
            raise ValueError(f'Input checksum mismatch: {name}')
    result = analyze(records, json.loads(args.metadata.read_text()))
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    with (args.output_dir / 'per_run.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result['runs'][0]))
        writer.writeheader()
        writer.writerows(result['runs'])
    render(result, args.output_dir)
    print(json.dumps(result['conditions'], indent=2))


if __name__ == '__main__':
    main()
