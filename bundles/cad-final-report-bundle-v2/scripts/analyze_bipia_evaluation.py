"""Verify recorded BIPIA-derived tier classifications offline, without models."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evaluate_bipia_candidates import load_candidates, metrics
from evaluate_benign_candidates import tier


def verify(data):
    audit, frozen = load_candidates()
    expected = {
        'corpus_sha256': audit['candidates_sha256'], 'source_commit': audit['source_commit'],
        'classifier_sha256': audit['classifier_sha256'],
        'script_sha256': hashlib.sha256((ROOT / 'scripts/evaluate_bipia_candidates.py').read_bytes()).hexdigest(),
    }
    if any(data.get(k) != v for k,v in expected.items()):
        raise ValueError('Corpus/source/model/scorer checksum mismatch')
    if data['normal_thresholds'] != [.35, .75] or data['counterfactual_high_pressure_thresholds'] != [.25, .65]:
        raise ValueError('Policy thresholds differ from protocol')
    rows = data['rows']
    if len(rows) != len(frozen) or len({r['id'] for r in rows}) != len(frozen):
        raise ValueError('Missing or duplicate rows')
    by_id = {r['id']: r for r in rows}
    for original in frozen:
        row = by_id.get(original['id'], {})
        if any(row.get(k) != v for k,v in original.items()):
            raise ValueError('Scored row differs from frozen source/context')
        if 'error' in row:
            continue
        probs = row['probabilities']
        risk = row['risk']
        if (set(probs) != {'benign', 'injection', 'exhaustion'} or
                any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()) or
                abs(sum(probs.values())-1) > 1e-6 or
                not math.isfinite(risk) or not 0 <= risk <= 1 or
                abs(risk-(1-probs['benign'])) > 1e-6):
            raise ValueError('Risk/probability inconsistency')
        if row['predicted_class'] != max(probs, key=probs.get):
            raise ValueError('Predicted class inconsistent with probabilities')
        if row['features']['session_repeat_count'] != 1:
            raise ValueError('Expected isolated first-session observations')
        if row['normal_tier'] != tier(risk, .35, .75) or row['counterfactual_high_pressure_tier'] != tier(risk, .25, .65):
            raise ValueError('Policy decision inconsistent with risk')
    recomputed = metrics(rows)
    if data['metrics'] != recomputed or data['total_scoring_errors'] != sum('error' in r for r in rows):
        raise ValueError('Aggregate metrics/errors differ from rows')
    changed = [r['id'] for r in rows if 'error' not in r and r['normal_tier'] != r['counterfactual_high_pressure_tier']]
    return {'verified_rows': len(rows), 'normal': recomputed['normal'],
            'counterfactual_high_pressure': recomputed['counterfactual_high_pressure'],
            'by_category_normal': recomputed['by_category_normal'],
            'by_category_counterfactual_high_pressure': recomputed['by_category_counterfactual_high_pressure'],
            'clean_controls': recomputed['clean_controls'], 'changed_decision_ids': changed,
            'limits': 'Controlled source-derived classification, not official BIPIA ASR or downstream attack success.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('output directory exists; choose a fresh path')
    data = json.loads(args.input.read_text())
    result = verify(data)
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'verified_summary.json').write_text(json.dumps(result, indent=2)+'\n')
    with (args.output_dir / 'all_outcomes.csv').open('w', newline='') as handle:
        fields = ['id', 'category', 'label', 'attack_text', 'risk', 'normal_tier',
                  'counterfactual_high_pressure_tier', 'predicted_class', 'error']
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data['rows'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), layout='constrained')
    colors = {'full':'#a9b0b8', 'sandbox':'#d39c4c', 'quarantine':'#b74d47'}
    left = [0, 0]
    for field in ('full', 'sandbox', 'quarantine'):
        values = [result[key][field] for key in ('normal', 'counterfactual_high_pressure')]
        axes[0].barh(['Normal', 'Tightened\n(counterfactual)'], values, left=left, color=colors[field], label=field)
        left = [a+b for a,b in zip(left,values)]
    axes[0].set(xlabel='Attack variants (75 total)', title='Tier decisions, not attack success rate')
    axes[0].legend(loc='center', ncol=3)
    categories = list(result['by_category_normal'])
    left = [0]*len(categories)
    for field in ('full', 'sandbox', 'quarantine'):
        values = [result['by_category_normal'][c][field] for c in categories]
        axes[1].barh(categories, values, left=left, color=colors[field])
        left = [a+b for a,b in zip(left,values)]
    axes[1].invert_yaxis()
    axes[1].set(xlabel='Variants (5 per category)', title='Normal thresholds, by source category', xlim=(0,5))
    fig.suptitle('Native classifier: BIPIA-derived controlled memo test\n'
                 'Fixed AI-authored wrapper; source-derived intent; no downstream LLM calls', fontsize=11)
    for extension in ('png', 'svg'):
        fig.savefig(args.output_dir / f'bipia_tier_coverage.{extension}', dpi=200)
    plt.close(fig)
    print(json.dumps({k:result[k] for k in ('verified_rows','normal','counterfactual_high_pressure','changed_decision_ids')}, indent=2))


if __name__ == '__main__':
    main()
