# Static versus adaptive gateway negative controls

## Result

Both modes quarantined all eight high-risk demands and completed all eight benign probes without failures. In both runs, backend counters increased by exactly 296 prompt tokens, 128 generated tokens and eight completed requests, matching only the benign traffic. No backend queue or high-pressure samples were observed.

The static mean benign HTTP response time was 309.148 ms; adaptive was 302.812 ms, a descriptive difference of 6.337 ms. With one run and eight probes per mode, this does not establish adaptive superiority, statistical equivalence, or a reliable P99. This is a necessary negative control: demands with risk around 0.994 are rejected by both policies even at normal pressure.

## Provenance and checks

The operator supplied exact [static JSON](evidence/static_adaptive_controls_20261018/gpu_static_control_native_v1.json) and [adaptive JSON](evidence/static_adaptive_controls_20261018/gpu_adaptive_control_native_v1.json). Both client/script records match the `e93a40a6e73134ef406de2df2483791dfa39776c` revision of the runner. Mode-checked preflight status identifies static and adaptive respectively. The server does not expose its source revision; the client revision is not independent server attestation.

Both runs report the same native classifier SHA-256 `25ea5790c5b0151e644322e1caa19329e5b8c73679b79cba4ad486c1c5ae2e05`, matching [native model metadata](evidence/native_burst_20261018/lab_native_v1_metadata.json). Workload configurations are identical after excluding mode-check/output-file fields. Cache telemetry confirms the same 256 MiB, 7,280-token, 455-block pool with prefix caching. The operator was instructed to restart both servers between modes; a complete backend process/startup audit was not included in these files.

The schedule was eight simultaneous short demand requests and eight benign probes staggered every three seconds. Demands requested 1,792 output tokens with forced-length `ignore_eos=true`; all were rejected. Probes requested 16 tokens. One benign warmup to each endpoint precedes measured counters even with gateway-only execution. The direct load arm was explicitly not run and is marked `executed=false`; its zero summary fields are not observations of a direct workload.

## Measurements

| Measurement | Static | Adaptive |
| --- | ---: | ---: |
| Demands quarantined | 8 / 8 | 8 / 8 |
| Benign completed / failed | 8 / 0 | 8 / 0 |
| Mean benign HTTP time | 309.148 ms | 302.812 ms |
| Observed benign min–max | 291.468–357.334 ms | 290.025–342.029 ms |
| Sampled peak KV occupancy | 0.660793% | 0.881057% |
| Peak backend waiting requests | 0 | 0 |
| Peak backend running requests | 1 | 1 |
| Backend prompt-token delta | 296 | 296 |
| Backend generated-token delta | 128 | 128 |
| Backend completed-request delta | 8 | 8 |
| Observed GPU 0 allocation | 7,428–7,522 MiB | 7,428–7,522 MiB |
| Telemetry samples / errors | 80 / 0 | 80 / 0 |

All 16 classified static requests recorded policy `static`; all 16 adaptive requests recorded policy `normal`. All captured endpoint states were below the high-pressure trigger. The small sampled occupancy difference does not establish a policy effect: both made identical tier decisions, requests have different schedules/durations, and sparse sampling may capture different instants.

No P99, energy/dollar saving, OOM prevention, or zero-GPU-work claim follows. These controls differ from the earlier direct/protected saturation calibration: they test the protected modes only, both at low occupancy. The earlier 99.56% direct pressure is not an exposure applied to these classified requests.

## Reproducible analysis

Exact inputs, per-mode SHA-256 digests, counter reconciliation, CSVs and PNG/SVG figures are retained:

- [Static derived JSON](evidence/static_adaptive_controls_20261018/static_analysis/derived_summary.json), [trial CSV](evidence/static_adaptive_controls_20261018/static_analysis/trial_metrics.csv), [telemetry CSV](evidence/static_adaptive_controls_20261018/static_analysis/telemetry_trace.csv), [PNG](evidence/static_adaptive_controls_20261018/static_analysis/burst_comparison.png), [SVG](evidence/static_adaptive_controls_20261018/static_analysis/burst_comparison.svg).
- [Adaptive derived JSON](evidence/static_adaptive_controls_20261018/adaptive_analysis/derived_summary.json), [trial CSV](evidence/static_adaptive_controls_20261018/adaptive_analysis/trial_metrics.csv), [telemetry CSV](evidence/static_adaptive_controls_20261018/adaptive_analysis/telemetry_trace.csv), [PNG](evidence/static_adaptive_controls_20261018/adaptive_analysis/burst_comparison.png), [SVG](evidence/static_adaptive_controls_20261018/adaptive_analysis/burst_comparison.svg).

Reproduce either mode into a new directory:

```bash
python scripts/analyze_gpu_burst.py \
  --input reports/evidence/static_adaptive_controls_20261018/gpu_static_control_native_v1.json \
  --metadata reports/evidence/native_burst_20261018/lab_native_v1_metadata.json \
  --output-dir /tmp/cad-static-analysis-new
```

Both real control files pass model-identity, matching-workload and backend-counter regression checks. All 32 CPU tests passed when adding this report and the next calibration tool. Actual new calibration scores have not been generated in the cloud because the native lab artifact binaries have not been supplied.

## Next: separately labeled mechanism-test calibration

An empirical dynamic-policy test needs classified requests in a changed risk band: 0.25–0.35 (full becomes sandbox), or 0.65–0.75 (sandbox becomes quarantine), exposed to real pressure above 0.85. These controls used far lower benign risks and far higher demand risks, so neither band's behavior was exercised.

`scripts/calibrate_policy_candidates.py` defines a fixed ten-prompt corpus before lab scoring, simulates 1–10 repeated requests per prompt in its own process and saves every score, features and counterfactual tier. The first candidate in each predefined risk band is identified by a disclosed deterministic rule. Empty bands remain empty. No model is retrained and no LLM generation is requested. The script loads MiniLM for feature extraction; initialization may perform ordinary model-cache metadata lookups. The repeat count is the application's accumulated session count, not a measured requests-per-second rate.

This is calibration-based input selection for testing the routing mechanism, not unbiased detection/false-positive evaluation. The corpus has no independent ground-truth attack labels and session repeats are deliberately varied. A subsequent live experiment must reproduce the selected session state by explicit priming, verify the same artifact hash/risk, apply comparable external backend pressure, and record actual decisions/counters in each mode. Counterfactual offline tiers do not prove real policy activation or efficacy. Held-out evaluation, larger repeated latency samples and production-context resource controls remain separate requirements.

On the lab, stop the gateway to avoid an extra active embedding-model copy, leave vLLM idle and run:

```bash
GATEWAY_MODELS_DIR=models/lab_native_v1 .venv/bin/python scripts/calibrate_policy_candidates.py --output results/policy_candidate_calibration_native_v1.json
```

The result preserves the full corpus, corpus checksum, all candidate scores, model hash, runtime and embedding device/dtype. It does not modify native model files or the stopped gateway's session state. Do not choose replacement prompts after seeing a desired comparative outcome and then present those results as held-out accuracy.
