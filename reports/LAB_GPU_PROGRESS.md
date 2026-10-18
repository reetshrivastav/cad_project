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
