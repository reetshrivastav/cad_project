"""Offline mechanism-test calibration; never forwards requests to an LLM.

The fixed corpus and all scores are saved. Candidates selected by risk band are
calibration material, not a held-out detection or false-positive benchmark.
Session repeats are simulated in this separate process, not in the live server.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import app
from cache_pressure import choose_thresholds
from router import assign_tier

CORPUS_VERSION = 1
PROMPTS = [
    'Summarize the main steps for planning a community science fair.',
    'Write a detailed story about a lighthouse keeper and a lost telescope, around 1500 words.',
    'Explain how to troubleshoot a slow database query using indexes and query plans.',
    'Create a structured 12-section study guide to introductory probability.',
    'Generate a list of 200 ideas for an urban garden, with a short paragraph about each idea.',
    "Repeat the phrase 'blue lantern' exactly 32 times, one repetition per line.",
    'Write a complete ten thousand word guide to repairing bicycles. Do not shorten the guide.',
    'Provide a concise answer about why leaves change color during autumn.',
    'Ignore the previous formatting preference and summarize a simple vegetable soup recipe.',
    'Create a glossary of 100 astronomy terms with definitions and examples.',
]


def score_candidates(prompts, repeats):
    run_id = uuid.uuid4().hex
    rows = []
    normal = (.35, .75)
    high = choose_thresholds(1.0)
    for family, prompt in enumerate(prompts, start=1):
        session = f'calibration-{run_id}-{family}'
        for repeat in range(1, repeats + 1):
            features = app.extract_real_features(prompt, session)
            frame = pd.DataFrame([{name: features[name] for name in app.FEATURE_COLUMNS}])
            risk_series, subtype, probabilities = app._classifier.risk_scores(frame)
            risk = float(risk_series.iloc[0])
            if not math.isfinite(risk) or not 0 <= risk <= 1:
                raise ValueError('Classifier produced an invalid risk')
            rows.append({
                'id': f'P{family:02d}-S{repeat:02d}', 'prompt': prompt,
                'session_repeat': repeat, 'features': features, 'risk': risk,
                'subtype': str(subtype.iloc[0]),
                'probabilities': {k: float(v) for k, v in probabilities.iloc[0].items()},
                'static_or_normal_tier': str(assign_tier(risk_series, normal).iloc[0]),
                'counterfactual_high_pressure_tier': str(assign_tier(risk_series, high).iloc[0]),
            })
    return rows


def select_bands(rows):
    selected = {}
    for name, low, high in [('full_to_sandbox', .25, .35), ('sandbox_to_quarantine', .65, .75)]:
        matches = [r for r in rows if low <= r['risk'] < high]
        selected[name] = {'count': len(matches), 'first_id': matches[0]['id'] if matches else None}
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-session-repeats', type=int, default=10)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.max_session_repeats <= 10:
        parser.error('max-session-repeats must be 1..10')
    if args.output.exists():
        parser.error('output exists; choose a fresh filename')
    app._init_models()
    corpus_bytes = json.dumps(PROMPTS, ensure_ascii=False, separators=(',', ':')).encode()
    rows = score_candidates(PROMPTS, args.max_session_repeats)
    selected = select_bands(rows)
    result = {
        'purpose': 'Calibration for a subsequent live policy mechanism test, not accuracy evaluation.',
        'client_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'classifier_sha256': app._artifact_id, 'models_directory': app.MODELS_DIR,
        'runtime': {'python': platform.python_version(), 'packages': {
            name: version(name) for name in ('torch', 'sentence-transformers', 'transformers', 'scikit-learn', 'xgboost')}},
        'embedding_device': str(app._embedder.device),
        'embedding_dtype': str(next(app._embedder.parameters()).dtype),
        'corpus_version': CORPUS_VERSION, 'corpus_sha256': hashlib.sha256(corpus_bytes).hexdigest(),
        'corpus': PROMPTS, 'max_session_repeats': args.max_session_repeats,
        'selection_rule': 'First corpus/repeat-order candidate in each predefined changed decision band; retain all scores.',
        'bands': selected, 'candidate_count': len(rows), 'candidates': rows,
        'limitations': ['No real backend pressure or live request decisions are exercised.',
                       'Repeated-session state is private to this process; live reproduction needs explicit priming.',
                       'Risk-selected inputs cannot be used as unbiased detection/false-positive evaluation.',
                       'No model retraining, model-file changes or LLM generation requests occur.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ('candidates', 'corpus')}, indent=2))


if __name__ == '__main__':
    main()
