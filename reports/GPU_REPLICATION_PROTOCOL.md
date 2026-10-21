# Prespecified native GPU stress replications

Status: prepared on 21 October 2026; real GPU runs are pending lab execution. Earlier calibration and controls are exploratory evidence, not replications from this schedule. This protocol leaves the application, trained model and benchmark workload unchanged.

## Model preservation

The exact operator-uploaded archive is retained at [cad-lab-native-v1.tar.gz](evidence/native_model_20261018/cad-lab-native-v1.tar.gz), with [archive_manifest.json](evidence/native_model_20261018/archive_manifest.json). All four artifact hashes and the included metadata match the native burst experiment. The archive is 289,105 bytes, SHA-256 `995c8c4cf9fb797ccd3e09c673bbf5a4e13f9540e3dd4cf29e01d6f316fd17ae`. Original published models and the lab's existing model directory are preserved.

The standard-library verifier reads bytes and metadata without loading executable joblib objects. Run both checks before testing:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/verify_native_artifacts.py &&
.venv/bin/python scripts/verify_native_artifacts.py --model-dir models/lab_native_v1 &&
.venv/bin/python -m unittest discover -s tests -v
```

Do not retrain or change packages during the schedule. Native runtime versions are recorded in [lab_native_v1_metadata.json](evidence/native_burst_20261018/lab_native_v1_metadata.json). Byte verification does not establish runtime compatibility or classification performance. In a new lab checkout the archived files can restore the separately versioned native model; do not extract over an existing directory.

## Fixed experiment

Run three fresh-server repetitions per condition, nine runs total, in the following balanced order. Each run uses one round, eight concurrent demands, eight staggered benign probes, 1,792 demand output tokens, temperature zero and forced demand decoding. The backend launcher retains the 256 MiB KV pool, four active sequences, 2,048 context and prefix caching. These resource limits match calibration, not the default full-cache deployment.

| Run ID | Measured condition | Gateway launcher mode | Benchmark arms |
| --- | --- | --- | --- |
| b1_direct | direct | static | direct |
| b1_static | static | static | gateway |
| b1_adaptive | adaptive | adaptive | gateway |
| b2_static | static | static | gateway |
| b2_adaptive | adaptive | adaptive | gateway |
| b2_direct | direct | static | direct |
| b3_adaptive | adaptive | adaptive | gateway |
| b3_direct | direct | static | direct |
| b3_static | static | static | gateway |

Restart both servers before **every row**, including between rows with the same mode. Keep the same GPU and launch flags; stop unrelated clients and dashboard traffic. Retain startup logs showing actual KV token capacity. Record external GPU load or temperature/clock changes that could confound results. Fresh processes reset prefix-cache/session state; fixed warmup still primes some prefixes. Scheduling, clocks and prefix sharing remain sources of variation. The fixed Latin-square order balances position but is not randomized or blinded.

Terminal 1: Ctrl+C the previous backend, wait for it to exit, then:

```bash
cd ~/cad_project
bash scripts/start_lab_vllm.sh
```

Terminal 2: Ctrl+C the previous gateway, then use the mode in the table, for example:

```bash
cd ~/cad_project
bash scripts/start_lab_gateway.sh static
```

For adaptive rows substitute `adaptive`. Wait for both servers to become ready. Terminal 3:

```bash
curl -fsS http://127.0.0.1:5000/api/status
```

Require readiness true, the native directory, intended mode and classifier SHA-256 `25ea5790c5b0151e644322e1caa19329e5b8c73679b79cba4ad486c1c5ae2e05`.

## Terminal 3 commands

For each direct row, replace only the output's run ID; the first run is:

```bash
.venv/bin/python scripts/benchmark_gpu_pilot.py \
  --arms direct --require-routing-mode static --rounds 1 \
  --demands-per-round 8 --benign-per-round 8 --probe-interval 3 \
  --attack-tokens 1792 --request-timeout 240 --ignore-eos \
  --target-pressure 0.85 \
  --output results/replication_v1/b1_direct.json
```

For a static row:

```bash
.venv/bin/python scripts/benchmark_gpu_pilot.py \
  --arms gateway --require-routing-mode static --rounds 1 \
  --demands-per-round 8 --benign-per-round 8 --probe-interval 3 \
  --attack-tokens 1792 --request-timeout 240 --ignore-eos \
  --output results/replication_v1/b1_static.json
```

For an adaptive row:

```bash
.venv/bin/python scripts/benchmark_gpu_pilot.py \
  --arms gateway --require-routing-mode adaptive --rounds 1 \
  --demands-per-round 8 --benign-per-round 8 --probe-interval 3 \
  --attack-tokens 1792 --request-timeout 240 --ignore-eos \
  --output results/replication_v1/b1_adaptive.json
```

The benchmark warms both endpoints before any measured condition; those requests are retained separately and excluded from measured totals. Even the direct-only run therefore requires a ready gateway. Gateway mode is held static in direct runs to fix that background configuration; it does not route measured direct requests.

Start with `b1_direct` and inspect its JSON before proceeding. If it fails or misses the pressure target, retain the file and inspect the cause rather than tuning the workload or discarding the result. On timeout or unexpected outcomes, stop the schedule and inspect outstanding backend work. Do not immediately repeat on a possibly busy backend. Use a new output name for an explicitly documented retry; retain both files. Never overwrite or silently replace a negative result.

## Prespecified analysis and scope

Report all outcomes, telemetry errors and target misses. Reconcile prompt/generation/success counters, request intervals and measured overlap for every run. Report per-run benign completion/failure counts, mean and range of benign HTTP latency, sampled peak KV fraction, peak waiting queue, token counts, GPU allocation ranges and actual request decision policies. Compare conditions within each block, then show all three per-run estimates and their range. Repetitions, not individual correlated concurrent requests, are the unit for the main comparison.

With only 24 benign probes per condition across three runs, do not estimate P99 or promise tail-latency guarantees. Three repetitions are a minimal engineering repeatability check; they do not supply strong statistical significance. Do not pool these with earlier exploratory runs as independent confirmatory repetitions.

Expected demand rejection by static and adaptive policies tests protection repeatability, not the incremental benefit of dynamic thresholds. Preserve equal or worse adaptive results. The changed-band calibration found no suitable prompts; no live changed-band efficacy claim follows from this schedule. This is capped synthetic generation, not a 100,000-word input, full-VRAM exhaustion, proof of OOM avoidance, natural-generation behavior, or measured monetary savings. Timeout cancellation, held-out security/FPR evaluation, conversation/session controls and ingress latency targets remain separate work.

When all scheduled runs are complete, collect their exact JSON and retained startup logs. For JSON alone:

```bash
tar -czf ~/Desktop/cad-gpu-replication-v1.tar.gz results/replication_v1
```

Upload that archive for counter reconciliation and the repeatability report. No real GPU results for this protocol have been produced in the cloud environment.
