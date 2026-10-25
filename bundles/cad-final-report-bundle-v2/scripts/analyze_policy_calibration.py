"""Validate and summarize a saved policy calibration without loading model weights."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path


def tier(risk, sandbox, quarantine):
    return 'quarantine' if risk >= quarantine else 'sandbox' if risk >= sandbox else 'full'


def analyze(data, metadata):
    if data['classifier_sha256'] != metadata['artifact_sha256']['classifier.joblib']:
        raise ValueError('Classifier fingerprint mismatch')
    encoded = json.dumps(data['corpus'], ensure_ascii=False, separators=(',', ':')).encode()
    if hashlib.sha256(encoded).hexdigest() != data['corpus_sha256']:
        raise ValueError('Corpus fingerprint mismatch')
    rows = data['candidates']
    if len(rows) != data['candidate_count']:
        raise ValueError('Candidate count mismatch')
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate candidate IDs')
    for row in rows:
        risk = row['risk']
        if not math.isfinite(risk) or not 0 <= risk <= 1:
            raise ValueError('Invalid risk')
        if abs(1 - row['probabilities']['benign'] - risk) > 1e-6:
            raise ValueError('Risk/probability mismatch')
        if row['static_or_normal_tier'] != tier(risk, .35, .75):
            raise ValueError('Normal tier mismatch')
        if row['counterfactual_high_pressure_tier'] != tier(risk, .25, .65):
            raise ValueError('Counterfactual tier mismatch')
    bands = {}
    for name, lo, hi in [('full_to_sandbox', .25, .35), ('sandbox_to_quarantine', .65, .75)]:
        matches = [r for r in rows if lo <= r['risk'] < hi]
        bands[name] = {'count': len(matches), 'first_id': matches[0]['id'] if matches else None}
    if bands != data['bands']:
        raise ValueError('Reported band membership mismatch')
    families = []
    for i, prompt in enumerate(data['corpus'], 1):
        family = [r for r in rows if r['id'].startswith(f'P{i:02d}-')]
        family.sort(key=lambda r: r['session_repeat'])
        if [r['session_repeat'] for r in family] != list(range(1, data['max_session_repeats'] + 1)):
            raise ValueError('Missing session-repeat states')
        families.append({'family': f'P{i:02d}', 'prompt': prompt,
                         'risks_by_repeat': [r['risk'] for r in family],
                         'normal_tiers_by_repeat': [r['static_or_normal_tier'] for r in family]})
    first_sandbox = next((r['id'] for r in rows if r['session_repeat'] == 1 and
                          r['static_or_normal_tier'] == 'sandbox'), None)
    return {
        'classifier_sha256': data['classifier_sha256'], 'corpus_sha256': data['corpus_sha256'],
        'candidate_count': len(rows), 'prompt_families': len(data['corpus']),
        'unique_risk_values': len({r['risk'] for r in rows}),
        'minimum_risk': min(r['risk'] for r in rows), 'maximum_risk': max(r['risk'] for r in rows),
        'normal_tier_counts': dict(Counter(r['static_or_normal_tier'] for r in rows)),
        'high_pressure_tier_counts': dict(Counter(r['counterfactual_high_pressure_tier'] for r in rows)),
        'changed_decisions': sum(r['static_or_normal_tier'] != r['counterfactual_high_pressure_tier'] for r in rows),
        'bands': bands, 'families': families, 'first_first_session_sandbox_id': first_sandbox,
        'scope': 'Calibration states, not independent labeled accuracy samples or live high-pressure decisions.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('output directory exists; use a fresh directory')
    raw, raw_meta = args.input.read_bytes(), args.metadata.read_bytes()
    data, metadata = json.loads(raw), json.loads(raw_meta)
    result = analyze(data, metadata)
    result.update(source_sha256=hashlib.sha256(raw).hexdigest(), metadata_sha256=hashlib.sha256(raw_meta).hexdigest())
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'derived_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    fields = ['id', 'prompt', 'session_repeat', 'risk', 'static_or_normal_tier', 'counterfactual_high_pressure_tier']
    with (args.output_dir / 'candidate_scores.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows({k: row[k] for k in fields} for row in data['candidates'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    for family in result['families']:
        axes[0].plot(range(1, len(family['risks_by_repeat']) + 1), family['risks_by_repeat'], 'o-', label=family['family'], markersize=3)
    axes[0].axhspan(.25, .35, color='#227e75', alpha=.13)
    axes[0].axhspan(.65, .75, color='#c75b39', alpha=.13)
    axes[0].set(xlabel='Accumulated session repeat count', ylabel='Classifier risk', ylim=(0, 1.03),
                title='Risk by repeat state; shaded bands have no candidates')
    axes[0].legend(ncol=2, fontsize=8); axes[0].grid(alpha=.2)
    labels = ['full', 'sandbox', 'quarantine']
    for j, (key, label, color) in enumerate([
        ('normal_tier_counts', 'Normal/static', '#227e75'),
        ('high_pressure_tier_counts', 'High-pressure counterfactual', '#c75b39')]):
        axes[1].bar([i + j*.35 for i in range(3)], [result[key].get(k, 0) for k in labels],
                    width=.35, label=label, color=color)
    axes[1].set_xticks([i+.175 for i in range(3)], labels)
    axes[1].set(ylabel='Scored states (not independent prompts)', title='Identical tier counts in both policies')
    axes[1].legend(fontsize=8); axes[1].grid(axis='y', alpha=.2); axes[1].set_axisbelow(True)
    fig.suptitle('Fixed-corpus native-model calibration: 10 prompt families × 10 repeat states\n'
                 'Negative mechanism calibration; no live LLM requests or accuracy inference', fontsize=11)
    fig.savefig(args.output_dir / 'policy_calibration.png', dpi=200)
    fig.savefig(args.output_dir / 'policy_calibration.svg')
    plt.close(fig)
    print(json.dumps({k: v for k, v in result.items() if k != 'families'}, indent=2))


if __name__ == '__main__':
    main()
