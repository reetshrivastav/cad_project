"""Score the frozen reviewed candidate pool using native live CUDA/FP16 features.

No web server, vLLM calls, retraining or model changes. AI annotations are not
independent human ground truth. Normal and counterfactual policies are separate.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
FROZEN = ROOT / 'reports/evidence/heldout_preparation_20261022/candidates.jsonl'


def load_labels(path):
    frozen = [json.loads(line) for line in FROZEN.read_text().splitlines()]
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(frozen[0]):
            raise ValueError('CSV columns differ from the frozen worksheet')
        rows = list(reader)
    if len(rows) != len(frozen):
        raise ValueError('Expected all 200 frozen rows; retain exclusions')
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != {r['id'] for r in frozen}:
        raise ValueError('Missing, duplicate or changed row IDs')
    ordered = []
    for original in frozen:
        row = by_id[original['id']]
        for key in original:
            if key not in ('label', 'reviewer', 'notes') and row[key] != str(original[key]):
                raise ValueError(f'{row["id"]}: frozen field changed: {key}')
        if hashlib.sha256(row['prompt'].encode()).hexdigest() != row['prompt_sha256']:
            raise ValueError('Prompt checksum mismatch')
        if row['label'] not in ('benign', 'injection', 'exhaustion', 'exclude') or not row['reviewer'].strip():
            raise ValueError(f'{row["id"]}: label/reviewer missing or invalid')
        if row['label'] != 'benign' and not row['notes'].strip():
            raise ValueError(f'{row["id"]}: explain non-benign/excluded label')
        ordered.append(row)
    return ordered


def tier(risk, sandbox, quarantine):
    return 'quarantine' if risk >= quarantine else 'sandbox' if risk >= sandbox else 'full'


def wilson(count, total):
    if total == 0:
        return None
    z = 1.959963984540054
    p = count / total
    denominator = 1 + z*z/total
    middle = (p + z*z/(2*total)) / denominator
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return [max(0, middle-half), min(1, middle+half)]


def policy_metrics(rows, field):
    benign = [r for r in rows if r['label'] == 'benign']
    scored = [r for r in benign if 'error' not in r]
    result = {'labeled_benign_total': len(benign), 'successfully_scored': len(scored),
              'scoring_errors': len(benign)-len(scored),
              'denominator': 'Successfully scored AI/human-labeled benign rows; errors reported separately, never counted as passes.'}
    for name, tiers in [('quarantine', {'quarantine'}), ('sandbox', {'sandbox'}),
                        ('any_restriction', {'sandbox', 'quarantine'})]:
        count = sum(r[field] in tiers for r in scored)
        result[name] = {'count': count, 'rate': count/len(scored) if scored else None,
                        'wilson_95_interval': wilson(count, len(scored))}
    return result


def score_rows(rows, score):
    results = []
    for row in rows:
        result = dict(row)
        if row['label'] == 'exclude':
            result['excluded'] = True
        else:
            try:
                scored = score(row['prompt'])
                risk = scored['risk']
                if not math.isfinite(risk) or not 0 <= risk <= 1:
                    raise ValueError('Risk must be finite in [0,1]')
                result.update(scored, normal_tier=tier(risk, .35, .75),
                              counterfactual_high_pressure_tier=tier(risk, .25, .65))
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--models-dir', type=Path, default=ROOT / 'models/lab_native_v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; choose a fresh filename')
    rows = load_labels(args.labels)  # Validate before model loading or GPU work.
    from verify_native_artifacts import verify
    model_dir = args.models_dir.resolve()
    verify(model_dir=model_dir)
    os.environ['GATEWAY_MODELS_DIR'] = str(model_dir)
    import app
    import pandas as pd
    app._init_models()
    if str(app._embedder.device).split(':')[0] != 'cuda' or str(next(app._embedder.parameters()).dtype) != 'torch.float16':
        raise SystemExit('Expected native live CUDA/FP16 embedding path; no scoring performed')

    def score(prompt):
        features = app.extract_real_features(prompt, f'heldout-{uuid.uuid4().hex}')
        if features['session_repeat_count'] != 1:
            raise ValueError('Expected isolated first-session state')
        frame = pd.DataFrame([{k: features[k] for k in app.FEATURE_COLUMNS}])
        risks, subtype, probabilities = app._classifier.risk_scores(frame)
        return {'risk': float(risks.iloc[0]), 'features': features,
                'predicted_class': str(probabilities.iloc[0].idxmax()),
                'threat_subtype': str(subtype.iloc[0]),
                'probabilities': {k: float(v) for k, v in probabilities.iloc[0].items()}}

    results = score_rows(rows, score)
    ai_only = all('AI-only' in r['reviewer'] for r in rows)
    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'client_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'labels_sha256': hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        'candidates_sha256': hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
        'classifier_sha256': app._artifact_id, 'models_directory': str(model_dir),
        'annotation_provenance': 'AI-only; no independent human adjudication' if ai_only else 'Reviewer fields supplied in CSV; independent adjudication not verified',
        'runtime': {'python': platform.python_version(), 'packages': {name: version(name) for name in
                    ('torch', 'sentence-transformers', 'transformers', 'scikit-learn', 'xgboost')}},
        'embedding_device': str(app._embedder.device),
        'embedding_dtype': str(next(app._embedder.parameters()).dtype),
        'normal_thresholds': [.35, .75], 'counterfactual_high_pressure_thresholds': [.25, .65],
        'metrics_normal': policy_metrics(results, 'normal_tier'),
        'metrics_counterfactual_high_pressure': policy_metrics(results, 'counterfactual_high_pressure_tier'),
        'excluded_rows': sum(r.get('excluded', False) for r in results),
        'total_scoring_errors': sum('error' in r for r in results),
        'rows': results,
        'limitations': [
            'Same-source screened sample with AI-only labels when indicated; not independent human ground truth.',
            'No representative attack recall, multiclass accuracy, deployed prevalence or causal adaptive benefit is estimated.',
            'Wilson intervals describe binomial sampling uncertainty conditional on labels; they do not cover annotation error or establish deployment generalization.',
            'No live backend pressure, LLM generation, HTTP routing or GPU cancellation is exercised.',
            'Each input is a fresh session; cumulative-session robustness is outside scope.',
            'Extraction times include cold samples and exclude classifier time; this is not a warmed latency benchmark.',
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps({k: report[k] for k in ('annotation_provenance', 'classifier_sha256',
          'embedding_device', 'embedding_dtype', 'metrics_normal',
          'metrics_counterfactual_high_pressure', 'excluded_rows', 'total_scoring_errors')}, indent=2))
    print(f'Output: {args.output}')
    if report['total_scoring_errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
