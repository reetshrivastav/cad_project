"""Offline native feature/risk/tier parity check; never forwards to vLLM."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
import pandas as pd
import torch
import app
from benchmark_embedding_paths import PROMPTS
from router import assign_tier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output filename')
    app._init_models()
    rows = []
    prompts = PROMPTS + ['', '🙂 café résumé', 'word ' * 1000]
    original = os.environ.get('GATEWAY_EMBEDDING_MODE')
    try:
        # Same prompt repeated per session exercises session-dependent features too.
        for index, prompt in enumerate(prompts):
            sessions = {mode: str(uuid.uuid4()) for mode in ('encode', 'direct')}
            for repeat in range(1, 4):
                outcomes = {}
                for mode in ('encode', 'direct'):
                    os.environ['GATEWAY_EMBEDDING_MODE'] = mode
                    features = app.extract_real_features(prompt, sessions[mode])
                    frame = pd.DataFrame([{key: features[key] for key in app.FEATURE_COLUMNS}])
                    risks, _, _ = app._classifier.risk_scores(frame)
                    risk = float(risks.iloc[0])
                    outcomes[mode] = {'features': {key: features[key] for key in app.FEATURE_COLUMNS}, 'risk': risk,
                                      'normal_tier': str(assign_tier(risks, (.35, .75)).iloc[0]),
                                      'high_pressure_tier': str(assign_tier(risks, (.25, .65)).iloc[0])}
                rows.append({'prompt_index': index, 'repeat': repeat, 'equal': outcomes['encode'] == outcomes['direct'], 'outcomes': outcomes})
    finally:
        if original is None:
            os.environ.pop('GATEWAY_EMBEDDING_MODE', None)
        else:
            os.environ['GATEWAY_EMBEDDING_MODE'] = original
    result = {'all_equal': all(row['equal'] for row in rows), 'cases': len(rows),
              'classifier_sha256': app._artifact_id, 'device': str(app._embedder.device),
              'dtype': str(next(app._embedder.parameters()).dtype), 'rows': rows,
              'scope': 'Fixed diagnostic corpus with three repeat states; not comprehensive security equivalence or accuracy.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, indent=2))
    if not result['all_equal']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
