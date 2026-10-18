# Lab GPU integration progress

This is a progress report, not a completed stress-test evaluation. Hardware results below were supplied by the operator in terminal transcripts on 18 October 2026; they were not independently run in the cloud checkout. Original raw transcripts have not yet been committed. Do not treat this document as a substitute for raw experimental evidence.

## Observed lab behavior

- Operator-reported workstation: Ubuntu, NVIDIA RTX A4000, 16 GB VRAM. The gateway's original environment uses PyTorch 2.5.1+cu121. vLLM runs in its own environment; its PyTorch version remains to be recorded.
- vLLM 0.31.0 served Qwen/Qwen2.5-3B-Instruct, FP16, max model length 4096, max sequences 4, prefix caching enabled, memory utilization 0.75.
- Initial FlashInfer sampling compilation failed because `/usr/bin/nvcc` rejected `--compress-mode=size`. Launching with `VLLM_USE_FLASHINFER_SAMPLER=0` completed startup. Model loading used 5.79 GiB; the startup log reported about 5.1 GiB available for KV-cache.
- Direct backend and gateway requests both produced a binary-search explanation: 37 prompt tokens, 24 generated tokens. Gateway classified the request FULL, risk 0.0041.
- A short request demanding a 100,000-word novel returned gateway HTTP 403, risk about 0.990. This was not a 100,000-word input payload.
- All nine existing empirical benchmark cases passed. That script has separate embedding/lexical initialization and is not a complete validation of the live FP16 gateway.
- Gateway initialization logged MiniLM `cuda:0`, `torch.float16`.
- Two live gateway extraction measurements were 179.43 ms and 191.15 ms. These do not meet the latency target. Warmed component profiling remains necessary.
- Live `vllm:kv_cache_usage_perc` was 0.0, telemetry fresh, normal thresholds 0.35/0.75. This metric is a fraction (1 means 100%), not overall allocated GPU VRAM.
- Locally mocked 0.9 pressure tightened thresholds to 0.25/0.65 and changed the expected tier boundaries. Real sustained high-pressure behavior remains untested.

## Known limitations

The lab warned about scikit-learn 1.9.0 artifacts loaded under 1.7.2 and an XGBoost serialization mismatch. Passing selected cases does not resolve cross-version compatibility. Record training versions and migrate/export artifacts under compatible runtimes rather than hiding warnings.

CUDA embeddings consume GPU compute even for quarantined requests. The defensible measurement is avoided backend LLM work/KV-cache allocation, with gateway GPU overhead measured separately. Dollar costs in `router.py` are illustrative estimates, not measured A4000 operating costs.

The five-second sandbox HTTP read timeout does not establish backend cancellation or a strict GPU execution deadline. The adapter currently classifies the last user message while forwarding the full conversation; aggregate context resource limits and full-conversation threat handling remain required. Prefix-cache reuse, queue pressure, concurrent benign latency, FP16 accuracy parity, and admission limits require further testing.

Do not infer zero backend allocation from flat `nvidia-smi`: vLLM preallocates cache memory. Use request/token counters and KV-block occupancy alongside memory and utilization measurements. Context-limit rejections by vLLM must be reported separately from gateway blocks.

## Reproducible next checks

Keep vLLM running with:

```bash
VLLM_USE_FLASHINFER_SAMPLER=0 .venv-vllm/bin/vllm serve Qwen/Qwen2.5-3B-Instruct --host 127.0.0.1 --port 8000 --dtype half --gpu-memory-utilization 0.75 --max-model-len 4096 --max-num-seqs 4 --enable-prefix-caching
```

Run CPU regression tests (no downloads or hardware required):

```bash
.venv/bin/python -m unittest discover -s tests -v
```

On the lab, profile actual MiniLM/extraction in a separate process with backend idle. Keep the gateway idle as well. This temporarily loads another MiniLM copy; stop the profiler before applying sustained load. Compare CPU thread configurations without changing model weights:

```bash
.venv/bin/python scripts/profile_ingress.py --output results/ingress_default.json
.venv/bin/python scripts/profile_ingress.py --cpu-threads 1 --output results/ingress_threads1.json
```

Output includes synchronized warm samples, distributions, versions, device/dtype, commit and dirty status. It excludes classifier, HTTP, and backend generation time. Do not label it end-to-end latency. Preserve files and use fresh names on repeat runs.

Live gateway routes use one telemetry snapshot per decision and conservative thresholds for missing/stale samples. Offline `assign_tier()` defaults to static thresholds so simulation results are reproducible without a live backend. To exercise adaptive policy directly, explicitly pass `thresholds=cache_pressure.choose_thresholds(pressure)`.

Before a stress-test report: resolve artifact compatibility, validate sandbox/backend cancellation and context limits, measure warmed ingress and live FP16 parity, then compare bounded direct-vLLM/static/adaptive runs with identical offered load and generation limits. Record raw time series, errors, completed tokens, request counters, KV occupancy, GPU memory/utilization and benign p50/p95/p99 latency. Report measured GPU-seconds separately from any dollar conversion and state its pricing assumptions. No GPU cost-savings percentage is established yet.

## Cloud regression validation for this change

Eight CPU regression tests passed via `python -m unittest discover -s tests -v`: labeled/multiple-engine metric parsing; invalid/missing metrics; pressure and exact threshold boundaries; stale telemetry; conversation and finish-reason forwarding; HTTP timeout handling; quarantine without a backend call; and sandbox caps with matching policy metadata. Python syntax compilation and `git diff --check` passed. These tests use mocks and do not establish lab GPU performance or backend cancellation. The profiler CLI was checked; actual CUDA profiling is pending execution on the lab.

## First warmed lab profiling runs

The operator pulled commit `397f6d82ab47434c468c618a10038debbfb2632f` and all eight regression tests passed on the lab host. The uploaded console transcript is retained in [evidence/lab_ingress_console.txt](evidence/lab_ingress_console.txt); exact extracted summaries and the transcript SHA-256 are in [evidence/ingress_console_summaries.json](evidence/ingress_console_summaries.json). Per-sample arrays remain in the lab's JSON outputs and have not yet been supplied here.

Both runs used NVIDIA RTX A4000, CUDA device 0, FP16, Python 3.10.12, 10 warmups and 100 measured samples of one short prompt. Reported actual packages: torch 2.13.0, sentence-transformers 3.4.1, transformers 5.17.0, scikit-learn 1.7.2 and xgboost 3.2.0. These differ from the originally reported PyTorch stack and the repository's Transformers pin. Pulling source does not synchronize installed packages. Do not force a downgrade or claim reproducible dependency compatibility until separate environment reconciliation is completed.

| Torch CPU threads | Extraction mean (ms) | Extraction p95 (ms) | Extraction p99 (ms) | Embedding mean (ms) | Embedding p99 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 24 (default) | 2.897 | 3.579 | 4.121 | 2.351 | 3.254 |
| 1 | 2.848 | 2.946 | 3.068 | 2.404 | 3.243 |

These isolated warmed measurements are lower than the previously observed live API timings but do not establish the cause of that difference. Embedding mean remains above 2 ms. Extraction excludes classifier, network and backend generation; a sub-5ms end-to-end ingress claim remains unproven. One short prompt and one run per configuration are insufficient to establish a general performance improvement or CPU thread optimum.

The transcript shows a progress bar for every encode call, because the application enables INFO logging and SentenceTransformer defaults to showing progress at that level. This change disables progress rendering explicitly in live extraction and the profiler's embedding-only call. Terminal I/O is unnecessary per-request overhead; its contribution to the earlier latency has not yet been quantified. Reprofile with fresh output names `results/ingress_default_quiet.json` and `results/ingress_threads1_quiet.json` before attributing any speedup. The original measurements are preserved unchanged.

## Warmed profiling with progress output disabled

The operator pulled `182f426154ae61b76f5ed58543d89c94c3f02103` and completed both repeat profiles. The console is preserved in [evidence/lab_ingress_quiet_console.txt](evidence/lab_ingress_quiet_console.txt); extracted summaries and its SHA-256 are in [evidence/ingress_quiet_console_summaries.json](evidence/ingress_quiet_console_summaries.json). Hardware, package versions, 10 warmups, 100 samples and prompt were the same as the initial profiles. Per-sample JSON files remain on the lab host.

| Torch CPU threads | Extraction mean (ms) | Extraction p95 (ms) | Extraction p99 (ms) | Embedding mean (ms) | Embedding p99 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 24 (default) | 2.647 | 2.758 | 2.883 | 2.082 | 2.222 |
| 1 | 2.651 | 2.790 | 2.825 | 2.118 | 2.340 |

Relative to each original run, extraction means were lower by about 8.6% and 6.9%, and embedding means by about 11.4% and 11.9%, respectively. These are descriptive comparisons of single sequential runs, not controlled causal estimates or statistical evidence of a general speedup. Sub-2ms mean embedding remains unachieved; no CPU thread configuration is selected as superior. Do not equate these isolated extraction measurements with live Flask or end-to-end classification latency.

The next check is `python scripts/check_live_gateway.py --output results/live_gateway_quiet.json` after restarting the gateway from current source. Keep vLLM running and otherwise idle. This sends 3 warmup and 10 measured benign requests with an eight-token output cap and unique session IDs, followed by one short sponge-demand request. It records HTTP errors, routing outcomes, live extraction timings and pressure snapshots. Output is retained even when a measured routing assertion fails; preflight/connection failures may prevent the run from starting. This is bounded functional checking, not a concurrent stress benchmark, and does not prove backend cancellation or zero backend work for the blocked request.

## Raw lab samples and first live gateway check

The operator supplied the five original JSON outputs in `cad-gpu-results.tar.gz`. Exact extracted file bytes are committed under [evidence/lab_gpu_run_20261018/](evidence/lab_gpu_run_20261018/); `manifest.json` records SHA-256 digests and byte counts. Each isolated profile contains 100 extraction and 100 embedding samples, plus metadata. The live file contains all three warmups, ten measured requests, quarantine response and telemetry snapshots. Earlier statements that raw arrays were unavailable are superseded by this upload.

The live check client ran commit `50ea2e507b7376a8317f9c1b2a8633df9b261e83`; the operator reports restarting the gateway in Terminal 2. The server does not expose a source revision, so that revision was not independently verified. All 13 benign requests succeeded; one short novel-demand request was rejected with HTTP 403 and risk about 0.990. First warmup extraction was 166.54 ms; later warmups were 7.03 and 6.97 ms. The 10 measured extractions averaged 6.357 ms, p95 7.8545 ms and p99 8.4269 ms. Their range was 4.24–8.57 ms. HTTP including backend generation averaged 156.462 ms, p99 160.289 ms. The quarantine HTTP response took 17.192 ms.

Final cache usage was 0.000323485 (about 0.03235%); telemetry was fresh and normal. All stored request policy snapshots were normal. This run does not exercise high-pressure adaptation. The initial pressure endpoint response was unsampled/conservative as designed, and recovered during the run.

Live extraction is slower than isolated warmed extraction. The current measurements do not isolate CPU scheduling, Flask request threads, GPU contention, clocks or other causes. A sub-5ms live ingress or sub-2ms embedding claim remains unsupported. HTTP generation time must not be called ingress overhead.

## Next: bounded GPU protection pilot

`scripts/benchmark_gpu_pilot.py` compares direct vLLM with the adaptive gateway. It sends a short 100,000-word *output-demand* prompt capped to 256 generated tokens, concurrently with one benign probe capped to 16 tokens. Defaults are two rounds per arm with alternating arm order, four demand requests total plus probes and two warmups. No actual 100,000-word input is sent. The gateway now forwards an explicit `temperature` parameter so both arms can request greedy sampling.

Each trial records raw HTTP outcomes, requested caps, backend usage counts, request intervals, selected Prometheus metrics and `nvidia-smi` memory/utilization/power CSV. Telemetry collection is approximate and can miss brief peaks. The trial fails validation on unexpected responses or telemetry errors and retains completed-trial data. Preflight failures prevent starting the workload. HTTP timeouts do not guarantee backend cancellation; if requests time out, stop the pilot and inspect outstanding vLLM requests before repeating.

This is a low-load instrumentation/functional pilot, not proof of GPU saturation, OOM prevention, sustained DoS resistance, dollar savings, static-vs-adaptive superiority or high-pressure behavior. Prefix-cache state persists across arms and GPU clocks are uncontrolled. With only two probes per arm, do not report a reliable tail-latency estimate. Reserved VRAM may remain flat while live KV-block occupancy changes. Pending artifact compatibility warnings remain in force.

Run with both servers active and no unrelated traffic:

```bash
python scripts/benchmark_gpu_pilot.py --output results/gpu_protection_pilot.json
```

The script has CPU tests for telemetry parsing and outcome validation; it has not been run against a GPU in the cloud. Hardware results must be supplied by the lab operator before any efficacy conclusion is added.

Cloud validation of the pilot change: all 15 CPU regression tests passed, including a mocked complete two-round pilot checking arm order, persisted outcomes and token accounting. Temperature forwarding is covered in adapter and sandbox route tests. The pilot CLI, Python syntax compilation and whitespace checks passed. No pilot GPU measurements have been executed here.

## Pilot executed and analyzed

The lab operator completed the bounded pilot and supplied its full JSON. See [GPU_PILOT_REPORT.md](GPU_PILOT_REPORT.md) for per-trial counter reconciliation, GPU allocation ranges, overlap, a CSV and exportable PNG/SVG figures. Both gateway demands returned 403; backend interval deltas match only benign requests in those trials. Across both rounds the gateway avoided the direct arm's 140 demand prompt tokens and 512 generated demand tokens. All benign probes completed.

This supersedes the earlier pending-pilot status. Cache usage stayed below 0.22%, queue depth was zero, all recorded gateway policies were normal, and GPU allocation was 12,404–12,412 MiB. No saturation protection, static-vs-adaptive benefit, zero VRAM delta or monetary savings is established. Raw evidence is retained under `reports/evidence/gpu_pilot_20261018/`. The offline analysis and all 18 CPU regression tests completed successfully; actual saturation testing remains pending.

## Dependency repair and live recheck

The operator's `pip check` identified SentenceTransformers 3.4.1 with incompatible Transformers 5.17.0 in the gateway environment. Installing Transformers 4.47.1 also selected huggingface-hub 0.36.2 and tokenizers 0.21.4. The next check exposed a duplicate vLLM 0.31.0 installation in that same environment. Distinct `sys.prefix` values verified `.venv` and `.venv-vllm` were separate. Removing only vLLM from `.venv` yielded a clean gateway dependency check; the separate vLLM environment had previously passed its check. No vLLM-environment downgrade was requested.

The repaired gateway passed the nine empirical cases and, after pulling `551d7d4da000581c4f56ee329dd4c2ec4be84c8e`, all 18 regression tests. The live recheck passed all 13 benign requests and quarantined the short demand with HTTP 403/risk 0.990. Mean warmed extraction was 5.748 ms (p95 6.775, p99 6.811); mean HTTP including generation was 154.488 ms (p99 157.036). Quarantine HTTP time was 22.068 ms. Final telemetry was fresh/normal, pressure 0.000298270 (about 0.02983%). These are operator-supplied console summaries, not the full recheck JSON; no statistical speedup is inferred from the previous run.

Raw repair/recheck console evidence is stored under [evidence/environment_repair_20261018/](evidence/environment_repair_20261018/). Earlier GPU pilot results retain their original, conflicting package versions and must not be relabeled as measurements of the repaired environment. The remaining sklearn/XGBoost warnings are not resolved by `pip check` or selected passing cases.

Read-only artifact inspection found embedded XGBoost snapshot/model version triples `3.4.1` and a scikit-learn `1.9.0` version marker in the classifier's label encoder. The cloud checkout has those versions and loads both classifier and TF-IDF without warnings. Its installed distribution metadata says XGBoost 3.4.1 requires Python >=3.12 and scikit-learn 1.9.0 requires >=3.11. The lab gateway is Python 3.10.12; matching both distributions therefore requires a separate Python >=3.12 environment. Inspection details and unchanged artifact SHA-256 hashes are in [artifact_runtime_inspection.json](evidence/environment_repair_20261018/artifact_runtime_inspection.json). This identifies a supported compatibility direction, not a complete lockfile or independent proof of the original training Python version.

Next prerequisite: check whether Python 3.12 is already installed and available disk space before preparing a separate matching gateway environment without sudo. Preserve `.venv`, `.venv-vllm`, models and existing results. Do not upgrade/downgrade the vLLM environment or suppress serialization warnings as a substitute for compatibility. Rerun relevant classification, live GPU and performance checks in the matching environment before designating it the canonical evaluation runtime.

## Revised route: lab-native model and pressure calibration

The operator elected to retrain under the working Python 3.10 environment rather than install Python 3.12. This is supported as a new, separately versioned model, with original artifacts/evidence retained. Training now supports `--output-dir`, records runtime and artifact/dataset hashes, and labels its accuracy as training-set resubstitution. Gateway and verification support `GATEWAY_MODELS_DIR`; status exposes the classifier hash. No native-lab training has yet been executed by the cloud agent.

The runner now supports capped bursts/staggered benign probes and explicit pressure targets, records live policy snapshots during telemetry sampling, and preserves errors. `GATEWAY_ROUTING_MODE=static` supports future ablation without editing code. The [GPU_BURST_PROTOCOL.md](GPU_BURST_PROTOCOL.md) provides exact lab commands and explains why more queued clients cannot fill the former 148,400-token pool with only four active 4096-token sequences. The new constrained 256 MiB pool is an explicitly controlled experiment; saturation, collapse and p99 improvement remain hypotheses requiring measurements, not promised outcomes.

Cloud verification of this revision: all 25 CPU tests passed, including a real tiny CPU classifier export with mocked embedding inputs, nonempty-output protection, static/adaptive policy handling, synchronized multi-request client orchestration, delayed probes, target-miss evidence retention, abort-on-unexpected-outcome behavior and rejecting burst files in the old plotting tool. CLI/syntax/whitespace checks passed. Original model files and dependency declarations were not changed. The actual lab-native model and real high-pressure GPU outcomes are pending operator execution.
