"""Profile the real gateway extractor on the lab host; never calls vLLM.

Run: python scripts/profile_ingress.py --output results/ingress_profile.json
Includes warmups, synchronized extraction timing, and embedding-only timing.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=100)
    parser.add_argument('--warmup', type=int, default=10)
    parser.add_argument('--cpu-threads', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1 or args.warmup < 1:
        parser.error('samples and warmup must be positive')
    if args.output.exists():
        parser.error('output already exists; choose a new filename to preserve evidence')
    if args.cpu_threads:
        torch.set_num_threads(args.cpu_threads)
    app._init_models()
    prompt = 'Explain binary search in one sentence.'

    def synchronize():
        if app._embedder.device.type == 'cuda':
            torch.cuda.synchronize(app._embedder.device)

    def measure(operation):
        synchronize()
        started = time.perf_counter()
        operation()
        synchronize()
        return (time.perf_counter() - started) * 1000

    def describe(values):
        return {key: float(value) for key, value in zip(
            ('mean_ms', 'p50_ms', 'p95_ms', 'p99_ms'),
            [np.mean(values), *np.percentile(values, [50, 95, 99])])}

    for i in range(args.warmup):
        app.extract_real_features(prompt, f'profile-warmup-{i}')
    extraction, embedding = [], []
    for i in range(args.samples):
        extraction.append(measure(lambda: app.extract_real_features(prompt, f'profile-{i}')))
        embedding.append(measure(lambda: app._embedder.encode(
            [prompt], convert_to_numpy=True, normalize_embeddings=True)))
    result = {
        'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'git_status': subprocess.check_output(['git', 'status', '--porcelain'], text=True),
        'python': platform.python_version(),
        'packages': {name: importlib.metadata.version(name) for name in (
            'torch', 'sentence-transformers', 'transformers', 'scikit-learn', 'xgboost')},
        'device': str(app._embedder.device),
        'dtype': str(next(app._embedder.parameters()).dtype),
        'gpu': torch.cuda.get_device_name() if torch.cuda.is_available() else None,
        'torch_threads': torch.get_num_threads(),
        'prompt': prompt, 'samples': args.samples, 'warmup': args.warmup,
        'extraction': describe(extraction), 'embedding': describe(embedding),
        'extraction_samples_ms': extraction, 'embedding_samples_ms': embedding,
        'scope': 'Separate process; no backend requests or classifier timing. Shared GPU contention may affect results.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('_samples_ms')}, indent=2))


if __name__ == '__main__':
    main()
