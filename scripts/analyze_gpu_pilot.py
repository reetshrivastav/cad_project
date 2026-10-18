"""Derive tables/plots from a recorded pilot; never contacts servers.

Run with --input <pilot.json> --output-dir <new-directory>.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def metric_values(samples, name):
    return [sum(row['value'] for row in sample.get('metrics', []) if row['name'] == name)
            for sample in samples if any(row['name'] == name for row in sample.get('metrics', []))]


def counter_delta(samples, name):
    # Missing boundary values must not be silently interpreted as zeros.
    if not samples:
        return None
    first = metric_values([samples[0]], name)
    last = metric_values([samples[-1]], name)
    if not first or not last:
        return None
    value = last[0] - first[0]
    if value < 0:
        raise ValueError(f'Counter reset during trial: {name}')
    return value


def derive(data):
    rows = []
    for trial in data['trials']:
        requests = trial['requests']
        demand = next(r for r in requests if r['kind'] == 'demand')
        benign = next(r for r in requests if r['kind'] == 'benign')
        samples = trial['telemetry']
        cache = metric_values(samples, 'vllm:kv_cache_usage_perc')
        gpu = {}
        for sample in samples:
            for fields in csv.reader(io.StringIO(sample.get('nvidia_smi_csv', ''))):
                if len(fields) != 6:
                    continue
                index, name, memory, total, utilization, power = (v.strip() for v in fields)
                entry = gpu.setdefault(index, {'name': name, 'memory_used_mib': [],
                                               'utilization_percent': [], 'power_watts': []})
                for key, value in (('memory_used_mib', memory), ('utilization_percent', utilization), ('power_watts', power)):
                    try:
                        entry[key].append(float(value))
                    except ValueError:
                        pass
        gpu_ranges = {index: {'name': values['name']} | {
            key: {'min': min(series), 'max': max(series)} for key, series in values.items()
            if key != 'name' and series} for index, values in gpu.items()}
        overlap = max(0, min(demand['ended_monotonic'], benign['ended_monotonic']) -
                      max(demand['started_monotonic'], benign['started_monotonic'])) * 1000
        rows.append({
            'round': trial['round'], 'arm': trial['arm'],
            'demand_http_status': demand.get('status'), 'demand_http_ms': demand['http_ms'],
            'benign_http_status': benign.get('status'), 'benign_http_ms': benign['http_ms'],
            'http_interval_overlap_ms': overlap,
            'observed_peak_kv_fraction': max(cache) if cache else None,
            'backend_prompt_tokens_delta': counter_delta(samples, 'vllm:prompt_tokens_total'),
            'backend_generation_tokens_delta': counter_delta(samples, 'vllm:generation_tokens_total'),
            'backend_successful_requests_delta': counter_delta(samples, 'vllm:request_success_total'),
            'peak_running': max(metric_values(samples, 'vllm:num_requests_running'), default=None),
            'peak_waiting': max(metric_values(samples, 'vllm:num_requests_waiting'), default=None),
            'telemetry_samples': len(samples), 'gpu_ranges': gpu_ranges,
            'benign_pressure_policy': benign.get('body', {}).get('router_meta', {}).get('pressure_policy'),
        })
    return rows


def plot(rows, directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = [f"R{r['round']} {r['arm']}" for r in rows]
    colors = ['#c75b39' if r['arm'] == 'direct' else '#227e75' for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    series = [([r['backend_generation_tokens_delta'] for r in rows], 'Backend generated tokens', 'tokens'),
              ([100 * r['observed_peak_kv_fraction'] for r in rows], 'Sampled peak KV-cache usage', '% of KV blocks'),
              ([r['benign_http_ms'] for r in rows], 'Benign response time', 'ms including generation')]
    for ax, (values, title, ylabel) in zip(axes, series):
        ax.bar(labels, values, color=colors)
        ax.set(title=title, ylabel=ylabel)
        ax.tick_params(axis='x', rotation=30)
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle('RTX A4000 bounded pilot: two rounds per arm; no cache saturation\n'
                 'Short output-demand prompt, 256-token cap, one benign probe per trial', fontsize=11)
    fig.savefig(directory / 'pilot_comparison.png', dpi=200)
    fig.savefig(directory / 'pilot_comparison.svg')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('output directory exists; use a fresh directory to preserve evidence')
    raw = args.input.read_bytes()
    data = json.loads(raw)
    rows = derive(data)
    args.output_dir.mkdir(parents=True)
    result = {'source_file': args.input.name, 'source_sha256': hashlib.sha256(raw).hexdigest(),
              'source_client_commit': data['client_commit'], 'trials': rows,
              'interpretation': 'Observed interval counts and sampled peaks, not dollar savings or saturation protection.'}
    (args.output_dir / 'derived_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    flat = [{k: v for k, v in row.items() if k not in ('gpu_ranges', 'benign_pressure_policy')} for row in rows]
    with (args.output_dir / 'trial_metrics.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    plot(rows, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
