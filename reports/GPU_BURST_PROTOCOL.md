# Lab-native retraining and controlled KV-pressure calibration

This protocol is a new experiment, not an extension of the old model's accuracy claim. It does not require Python 3.12 or changing the vLLM environment. It preserves all previously published artifacts and evidence.

## What the existing pilot did and why a bigger client burst alone is insufficient

The original pilot hard-coded one demand plus one benign request and capped demand output to 512 tokens. The runner now accepts configurable demand/probe counts, staggered probes, up to 2048 demand output tokens, a configurable HTTP deadline, optional forced-length synthetic decoding, and an observed-pressure target. Defaults preserve the original two-request pilot.

The previous startup reported 148,400 KV tokens. With four active sequences and maximum context 4096, the active sequence-token ceiling is approximately 16,384 tokens, or 11.0% of that pool before accounting for prefix sharing. More client requests can queue but do not increase the engine's active-sequence cap. Four roughly 1024-token outputs from short inputs would occupy only a few percent of the original pool. Queueing is therefore distinct from cache exhaustion.

The current high-pressure policy triggers only above **0.85**, not 0.75 or 0.80. Risk-0.994 demands are quarantined by both normal/static and adaptive policies; rejecting them alone cannot demonstrate an incremental dynamic-threshold benefit. No collapse or latency improvement is assumed.

## 1. Retrain as a separate model version

Stop gateway in Terminal 2 and vLLM in Terminal 1 (Ctrl+C in each). From Terminal 3:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python -m pip check &&
.venv/bin/python -m unittest discover -s tests -v &&
.venv/bin/python train_on_datasets.py --output-dir models/lab_native_v1 &&
GATEWAY_MODELS_DIR=models/lab_native_v1 .venv/bin/python verify_empirical_pipeline.py
```

The explicit output directory must be empty or absent. Existing `models/*.joblib` and reports remain unchanged. The new metadata records package versions, dataset hashes, artifact hashes and **training-set** accuracy. That number is not held-out accuracy and must not be reported as retaining the prior 98.41%. The nine-case suite is a smoke test with overlap with training material, not an independent generalization evaluation. If training or verification fails, retain logs and stop before load testing. Training time is hardware/dataset dependent; 15 seconds is not guaranteed.

## 2. Use an explicitly constrained KV pool

In Terminal 1, use the supported `--kv-cache-memory` spelling shown by this lab's vLLM 0.31.0 startup logs. Check `vllm serve --help=all` if a different release is installed; do not substitute a guessed flag.

```bash
cd ~/cad_project
VLLM_USE_FLASHINFER_SAMPLER=0 .venv-vllm/bin/vllm serve Qwen/Qwen2.5-3B-Instruct --host 127.0.0.1 --port 8000 --dtype half --gpu-memory-utilization 0.75 --kv-cache-memory 268435456 --max-model-len 2048 --max-num-seqs 4 --max-num-batched-tokens 2048 --enable-prefix-caching
```

`268435456` bytes is a **256 MiB KV pool**, not a limit on total GPU allocation. Explicit KV capacity overrides the automatic cache sizing derived from memory utilization. The weight allocation and other runtime memory remain separate. The old observed 5.1 GiB pool maps roughly to 7,000–8,000 tokens at 256 MiB, but startup must establish the actual capacity. It must fit at least one 2048-token sequence. Preserve the startup output including token capacity and any allocation error. This configuration intentionally imposes a small resource budget; it is not the default A4000 deployment or a full-VRAM-exhaustion test.

In Terminal 2:

```bash
cd ~/cad_project
GATEWAY_MODELS_DIR=models/lab_native_v1 GATEWAY_ROUTING_MODE=adaptive .venv/bin/python app.py
```

In Terminal 3, verify artifact identity, mode and readiness:

```bash
curl -fsS http://127.0.0.1:5000/api/status
```

Require `models_directory` to end in `models/lab_native_v1`, a non-null `classifier_sha256`, `routing_mode=adaptive` and readiness flags true. If the new artifacts are incomplete the gateway fails rather than silently retraining defaults.

## 3. Calibrate, do not assume the pressure target is reached

Run with no unrelated traffic, both servers active:

```bash
.venv/bin/python scripts/benchmark_gpu_pilot.py --rounds 1 --demands-per-round 8 --benign-per-round 8 --probe-interval 3 --attack-tokens 1792 --request-timeout 240 --ignore-eos --target-pressure 0.85 --output results/gpu_burst_calibration_native_v1.json
```

Eight demands start together. Eight benign probes are scheduled at 0, 3, ..., 21 seconds, so probes are not all finished at burst startup. Each demand has a short prompt plus at most 1792 output tokens; inspect the backend's actual usage/context-limit errors. The request contains an explicit `ignore_eos=true` for demands, forwarded consistently by both paths: this is forced-length synthetic compute load, not evidence that the natural-language request alone forces unbounded generation. All generation remains capped. Unique request identifiers limit complete prefix reuse; prefixes are still retained/shared, not reset.

The direct and gateway arm each receive the same offered request schedule. The backend still executes at most four requests at a time; the client has sixteen workers. The HTTP timeout is not cancellation, and the gateway's own backend read deadline remains 90 seconds (five seconds for sandbox). Report timeout discrepancies; do not count dropped or timed-out benign requests as successful latency samples. The runner stops after an unexpected measured outcome and saves partial results rather than starting another arm on possibly outstanding work. If a request times out, inspect outstanding vLLM work before repeating. Do not immediately rerun on an undrained backend.

The runner retains raw telemetry, live gateway policy snapshots, request outcomes and model identity from status; training metadata records package versions. It prints `target_pressure_reached`; missing the direct-arm target yields a nonzero exit with the evidence file retained. High-pressure **telemetry** observations and actual adaptive-policy observations are counted separately, including when the gateway is serving no classified requests in the direct arm. Observing a high-pressure endpoint state alone is not a proof of changed request decisions or improved fairness.

The target may be missed because of prefix sharing, early scheduling changes, sampling or engine capacity. Inspect the actual peak, capacity, queue and request failures before adjusting the pool/output cap. A target miss is not a license to label the run saturated. Do not try to force an OOM.

Only eight benign probes per arm are used for this calibration: the runner reports no p99 with fewer than 100 successful probes. Even a later p99 from more samples needs repeated runs, failed-request counts and uncertainty analysis before a paper claim. The old two-request plotting script explicitly refuses burst files rather than discarding extra requests.

## 4. Required follow-up before claiming an adaptive-policy benefit

Once calibration is measured, plan repeated direct/static/adaptive comparisons. The gateway supports `GATEWAY_ROUTING_MODE=static` using base 0.35/0.75 thresholds while recording real pressure; use the same model directory/hash and restart it between modes. Restart the backend between independent runs when resetting cache state, preserving identical flags and warmup. Balance run order and account for thermal/clock effects.

To distinguish adaptive from static policies, use independently selected traffic whose risks lie in the changed decision bands (0.25–0.35 or 0.65–0.75), and comparable exogenous backend pressure when appropriate. The highest-risk demands in this calibration are blocked by either policy. If protection keeps the adaptive arm below its pressure threshold, that does not prove threshold tightening caused the benefit. Retain negative results rather than choosing prompts after seeing an outcome.

Live FP16 parity, held-out detection/false-positive evaluation, full-conversation/context controls, sandbox cancellation and precise ingress profiling remain separate work. Native retraining removes serialization version mismatch; it does not automatically validate those properties. No GPU-dollar or publication-readiness conclusion follows from this calibration alone.
