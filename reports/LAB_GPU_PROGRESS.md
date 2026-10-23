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

## Native burst calibration received

The lab operator supplied full native-model metadata and a complete burst JSON. The classifier hash matches the running gateway. Native training took 15.1 seconds, reported 98.24% **training-set** accuracy, and passed nine smoke cases and 25 regression tests. Actual native binary artifacts have not yet been uploaded; original published models remain untouched.

The controlled 256 MiB/7,280-token cache experiment reached 99.56% direct occupancy and a waiting queue of 13, versus 0.88% and no sampled queue protected. All benign requests completed; their means were 52.531 s direct and 0.299 s protected. Counters corroborate avoidance of 616 demand prompt tokens and 14,336 generated demand tokens. All protected request policies were normal; 36 high-pressure endpoint samples occurred only during direct load. This demonstrates constrained-resource admission protection, not an isolated adaptive-threshold benefit or P99 guarantee.

See [GPU_BURST_REPORT.md](GPU_BURST_REPORT.md) for raw evidence, checksums, per-request/counter analysis, telemetry CSVs and exportable figures. The updated runner supports gateway-only/static-mode-checked negative controls, with identical launcher scripts and fresh-cache instructions in the burst protocol. All 29 CPU tests passed; real static-control results are pending. Earlier statements that actual high-pressure behavior was unobserved are superseded by this calibration, while full-VRAM/OOM, default-cache, held-out generalization and causal adaptation claims remain unproven.

## Static/adaptive negative controls verified

Both exact control files were supplied. Mode and classifier fingerprints match the native metadata; workload and cache settings match. Each mode blocked all eight demands and completed eight benign probes, with backend deltas of 296 prompt tokens, 128 generated tokens and eight successful requests. Static averaged 309.148 ms benign HTTP time; adaptive 302.812 ms. No waiting queue or high-pressure sample occurred. All static requests used static thresholds; all adaptive requests used normal thresholds.

See [STATIC_ADAPTIVE_CONTROL_REPORT.md](STATIC_ADAPTIVE_CONTROL_REPORT.md) for raw evidence, checksums, CSVs, figures and limitations. These low-sample controls show no isolated adaptive-policy advantage; the six-millisecond descriptive difference is not a statistical result. This supersedes the earlier pending-static-control status.

Next, a fixed-corpus offline calibration tool records all scores and identifies any candidates in changed decision bands. Selection is explicitly for a subsequent mechanism test, not accuracy evaluation; no LLM requests, native-model changes or live session-state changes occur. Native binary artifacts are still retained on the lab rather than in the repository. All 32 CPU regression tests passed; actual native calibration and live pressure-conditioned request tests remain pending.

## Negative changed-band calibration received

The full 100-state, ten-family native calibration was supplied and its classifier/corpus checksums, probabilities, tier rules and band counts verified. Normal and high-pressure counterfactual policies both produced 32 full, four sandbox and 64 quarantine decisions, with zero changed decisions and no candidates in either changed band. All families jumped above 0.98 on the fifth repeat; the current session feature is a cumulative count without time-based decay, not a measured request rate.

See [POLICY_CALIBRATION_REPORT.md](POLICY_CALIBRATION_REPORT.md) for exact inputs, analysis, all-score CSV, figures and limitations. The result is preserved as negative mechanism calibration, not an accuracy/FPR estimate. No adaptive efficacy conclusion is inferred or desired outcome forced. A first-session sandbox candidate at risk 0.477339 supports the next actual 256-token enforcement check. The new live-check tool records cap/timeout metadata and post-response counters without treating an HTTP timeout as GPU cancellation. All 35 CPU tests passed; the actual lab sandbox check is pending.

## Live sandbox cap verified

The full native sandbox JSON confirms HTTP 200, a 256-token length-limited completion despite a requested 1,024 tokens, and matching backend interval deltas of 42 prompt tokens, 256 generated tokens and one length completion. All four post-response samples were idle with unchanged generation counters over 3.014 seconds. The native classifier hash matches calibration. See [SANDBOX_VALIDATION_REPORT.md](SANDBOX_VALIDATION_REPORT.md) for preserved raw evidence, checksum and limitations.

The decision used conservative startup telemetry, not actual high pressure. The request completed in 4.608 seconds, so no timeout/cancellation or hard GPU deadline was tested. This supersedes the pending sandbox status above; adaptive causal benefit and held-out security performance remain unproven. No application code or native model was changed for this report.

## Native artifact preservation and repeatability protocol (21 October 2026)

The operator's 289,105-byte native archive is retained under `reports/evidence/native_model_20261018/`. All four artifact hashes and the included metadata match the recorded native experiment. The archive checksum is recorded in its manifest. Verification uses bytes/JSON only, without deserializing joblib files; no model/runtime compatibility claim is inferred. Existing default models and lab-native directories are preserved.

[GPU_REPLICATION_PROTOCOL.md](GPU_REPLICATION_PROTOCOL.md) prespecifies three fresh-server repetitions of direct/static/adaptive conditions in balanced order, using the unchanged bounded workload and constrained KV pool. All outcomes, failed runs and target misses must be retained. The first next lab action is `b1_direct`; actual replication results remain pending. This is a small repeatability study, not a P99 or adaptive-superiority claim.

## Nine GPU replication runs verified (21 October 2026)

All nine scheduled files were supplied. All request outcomes passed and all backend prompt/generation/success deltas reconcile with responses; zero telemetry errors were recorded. Each condition completed 24/24 benign requests across three runs. Static and adaptive each quarantined all 24 demand requests. Direct run-mean benign HTTP latency ranged 47.393–55.629 seconds, static 298.510–306.859 ms, adaptive 297.100–299.919 ms. Sampled direct KV peaks were 99.56–100%, versus 0.88% protected; direct waiting peaks were 11–12, protected zero.

See [GPU_REPLICATION_REPORT.md](GPU_REPLICATION_REPORT.md) for exact evidence, checksums, per-run CSV, PNG/SVG figures, avoided-token accounting and limitations. All adaptive request policies were normal: repeatability of admission protection is established for this constrained synthetic workload, but an incremental adaptive-policy advantage remains unproven. The first direct file used the earlier client commit with the same benchmark hash; the preflight-only backend-readiness interruption is disclosed. Startup logs and per-run package snapshots were not supplied.

This supersedes the pending replication status. The next evaluation priority is an independent frozen held-out security/benign corpus with overlap checks and false-positive metrics; timeout/cancellation, conversation/session robustness and ingress targets remain separate open work.

## Held-out data exposure audit and candidate preparation (22 October 2026)

The checksum-verified training recipe uses all 520 AdvBench source goals. A new split of that file is not held out for the native model. Reconstructed training counts match metadata: 2,700 benign, 994 injection and 635 exhaustion rows, with 810/849/31 normalized unique prompt texts respectively (session states are not counted as unique text). No model, threshold or GPU-serving code changed.

[HELDOUT_EVALUATION_PREPARATION.md](HELDOUT_EVALUATION_PREPARATION.md) documents the audit and a frozen 200-row, unscored Alpaca candidate pool from source indices 800–999. Normalized exact and token-set Jaccard screening found no exclusions against training/references/known smoke/calibration and previously selected candidates. Same-source candidate status is not independent benign ground truth or a semantic contamination guarantee. Label/reviewer fields remain blank, and no accuracy/FPR/recall was computed. The next dependency is score-blind label review; independent attack evaluation still needs a separate corpus.

## AI annotation returned and benign scoring tool prepared (22 October 2026)

At the user's request the assistant annotated the frozen 200 prompts without seeing model scores; all were judged benign under the stated security criteria. The returned CSV exactly matches the assistant-created bytes, with all immutable prompt/ID/source/hash fields intact. The reviewer is explicitly AI-only, with no human adjudication claimed. Original blank evidence is preserved; annotation CSV and manifest are retained separately.

The benign scoring tool validates the complete frozen pool and annotation fields before loading the verified native model, requires CUDA/FP16, and uses the real application extractor with private first-request sessions. It records all rows and errors, distinct normal/counterfactual policies, separate quarantine/sandbox/any-restriction rates and conditional Wilson intervals. This is an AI-labeled same-source screened sample, not independent human ground truth or unseen attack evaluation. No real native scoring result has yet been supplied.

Cloud validation for this scoring revision: all 50 CPU tests passed, including CSV mutation/duplicate/blank-label rejection, inclusive policy boundaries, failed-score denominators, excluded-row behavior and nonzero uncertainty for zero observed events. Actual lab CUDA scoring remains pending.

## Native benign scoring evidence verified (22 October 2026)

All 200 frozen AI-labeled benign rows were scored on native CUDA/FP16, with zero errors or exclusions. Hashes, row integrity, probabilities, risk, first-session state, both policy decisions and reported rates reconcile offline. Normal thresholds produced four quarantines (2%), nine sandbox cases (4.5%), and 13 any restrictions (6.5%). Counterfactual tightened thresholds produced six quarantines (3%), eight sandbox cases (4%), and 14 any restrictions (7%). These are conditional on AI-only labels, without independent human adjudication.

[BENIGN_AI_LABELED_EVALUATION_REPORT.md](BENIGN_AI_LABELED_EVALUATION_REPORT.md) preserves raw evidence, all affected prompts, conditional intervals and PNG/SVG figures. The four normal quarantines are ordinary short requests with highest-probability injection classifications. Three natural changed-band cases are now observed in this separate corpus; they do not demonstrate live adaptive benefit, and score-selected follow-up use is mechanism/development testing. The earlier calibration's negative result remains valid for its own corpus.

This supersedes pending native scoring status. The exact native baseline is preserved; no labels, thresholds or model weights were changed to improve outcomes. Independent attack evaluation and stronger label adjudication remain pending, alongside conversation/session and timeout/cancellation work.

## External-source controlled injection corpus frozen (22 October 2026)

The next classification experiment uses all 75 published BIPIA text test attack strings (15 categories, five variants each) from pinned Microsoft commit `a004b69ec0dd446e0afd461d98cb5e96e120a5d0`. Source bytes, license, README and hashes are preserved. Because many strings are benign standalone requests, their source attack intent is tested only after insertion into a fixed AI-authored untrusted memo, with one clean control. All 76 constructed prompts were frozen without risk scores; both payloads and wrapped prompts passed the declared training/reference/prior-corpus lexical overlap checks.

[BIPIA_CONTROLLED_EVALUATION_PROTOCOL.md](BIPIA_CONTROLLED_EVALUATION_PROTOCOL.md) supplies the lab command and prespecified scope. Coverage is a controlled last-user-prompt tier classification outcome, not official BIPIA ASR, real tool-context ingestion, downstream LLM resistance or adaptive benefit. Source-derived attack intent and AI-authored context are explicitly distinguished from independent human labels. No model, threshold or previously frozen scoring script changed; actual native results remain pending.

## BIPIA-derived controlled scoring verified (23 October 2026 report; 22 October lab run)

All 76 observations reconcile with the frozen source/wrapper corpus and native model hashes. Normal thresholds selected quarantine for 1/75 source-derived attack variants, sandbox for 2/75 and full for 72/75, with zero scoring errors. The clean memo received full at risk 0.007945. Tightened counterfactual thresholds moved one sandbox variant to quarantine but left all 72 full decisions unchanged. Only Base Encoding and Substitution Ciphers had restricted cases; the other 13 categories had none.

[BIPIA_CONTROLLED_EVALUATION_REPORT.md](BIPIA_CONTROLLED_EVALUATION_REPORT.md) preserves negative outcomes, raw JSON/checksum, all-outcome CSV, category figures and scope limits. This is low classification coverage against controlled source-derived labels, not official BIPIA ASR or proof that an LLM followed the attacks. It does not invalidate measured resource protection, but prevents extending that evidence into general injection-security claims. The report discloses one stale inherited preparation-stage limitation in the immutable raw file.

The external-source controlled scoring stage is complete. The native v1 baseline remains unchanged. Next revision work must define trust-aware input scope and group-separated training/validation with a fresh untouched test set; these inspected examples can serve diagnostics/regressions, not fresh held-out evaluation after tuning.

## Specialized detector shadow comparison prepared (23 October 2026)

A separate ProtectAI DeBERTa v2 candidate is pinned to the revision referenced by its published LLM Guard scanner. The shadow script uses the 200 already-inspected AI-labeled benign cases, 75 constructed attack variants and one clean control; this is not fresh held-out evidence and candidate upstream training overlap is unknown. The prespecified binary operating points are >0.92 (observed scanner default) and >0.50. Native gateway weights, thresholds and serving paths remain unchanged.

[INJECTION_CANDIDATE_DIAGNOSTIC_PROTOCOL.md](INJECTION_CANDIDATE_DIAGNOSTIC_PROTOCOL.md) documents first-download needs, exact label validation, safetensors/no remote-code loading, no silent truncation, error preservation, metadata capture and limits. Cloud destination policy denied Hugging Face model access; no candidate weights/tokenizer/card or native inference were validated here. The lab command uses the existing gateway environment with both serving processes stopped. Actual diagnostic outcomes are pending and must not be described as an injection fix.

## Specialized candidate diagnostic verified; clean control failed (23 October 2026)

All 276 candidate observations reconcile with the frozen diagnostic cases and both prespecified thresholds. At >0.92 and >0.50, the candidate flagged 75/75 constructed attacks and 0/200 AI-labeled benign prompts, but also 1/1 clean memo, with probability 0.9999969. No errors/truncation occurred. Model/tokenizer/card loading succeeded on the lab with the pinned revision and CUDA/FP16, resolving the previous pending-access status; uploaded weight hashes are recorded, not independently rehashed in the cloud.

[INJECTION_CANDIDATE_DIAGNOSTIC_REPORT.md](INJECTION_CANDIDATE_DIAGNOSTIC_REPORT.md) preserves raw results/card, per-case CSV, figures, timing/memory observations and the control failure. The strong attack flag count does not establish attack-specific discrimination because the clean common wrapper is also flagged. Forty-four attack scores were below the clean score. This is development/diagnostic evidence, not fresh held-out validation or proof of downstream protection.

The candidate remains outside live routing. Next is prespecified matched wrapper/content ablation before integration; neither labels, original model, gate thresholds nor serving code were changed to improve the result. The current resource-protection evidence remains separate from this unresolved injection-specificity issue.

The matched wrapper follow-up is now frozen and scripted: four guard/tag cells, each with 75 source attacks, a clean memo and a harmless appendix (308 cases). The original guarded/tagged cell exactly reproduces the prior 76 prompts. The lab runner reuses cached pinned weights and verifies their digest. All 71 CPU tests passed; actual follow-up inference remains pending. See [WRAPPER_DIAGNOSTIC_PROTOCOL.md](WRAPPER_DIAGNOSTIC_PROTOCOL.md).

## Matched wrapper evidence verified; no live integration (23 October 2026)

All 308 observations reconcile with frozen cases, scripts, prior result and recorded pinned model artifacts. At >0.92, attack flags across guard+tags / guard-only / tags-only / neither were 75/75, 75/75, 70/75 and 1/75; at >0.50 tags-only rose to 73/75 and other counts stayed unchanged. Both harmless controls were flagged in all cells containing guard or tags, and passed when both were absent. No scoring errors occurred.

[WRAPPER_DIAGNOSTIC_REPORT.md](WRAPPER_DIAGNOSTIC_REPORT.md) retains raw data, paired probabilities, all outcomes, figures and interpretation. This supports wrapper sensitivity on matched development inputs, not task-relative injection efficacy. The candidate stays offline; removing safety wording or tuning a cutoff is not a demonstrated fix. The planned wrapper diagnosis is complete; the next injection revision requires an explicit task/trust input/label contract and new group-separated data with untouched evaluation.

[CURRENT_STATUS.md](CURRENT_STATUS.md) consolidates measured evidence and remaining gaps. README's opening/architecture claims now distinguish demonstrated constrained resource protection from unresolved injection/latency/zero-cost claims; original experimental artifacts and model weights remain unchanged.

## Task/content v2 representation prototype prepared (23 October 2026)

A separate offline prototype receives trusted task and untrusted content as distinct strings and uses frozen MiniLM CUDA/FP16 embeddings with pair interactions. Pair, task-only and content-only XGBoost models use identical fixed hyperparameters. No new detector download, v1 replacement, serving route, threshold change or trust-claiming client API was added.

The new 400-case AI/programmatic synthetic corpus has topic-family-disjoint 280/60/60 train/validation/test splits. Eighty distinct content texts have contrasting task-dependent workflow labels. Metadata is excluded from features, duplicate pairs/group leakage are rejected, trainer never encodes/scores test inputs, and test evaluation is a separate command. Templates are shared across splits, so these are controlled sanity checks rather than independent real-world/novel-template accuracy measurements.

[CONTEXT_V2_PROTOTYPE_PROTOCOL.md](CONTEXT_V2_PROTOTYPE_PROTOCOL.md) supplies the exact input/label contract, new-directory export, hash/revision checks and lab commands. Cloud checks use fake embeddings and tiny real CPU XGBoost models solely to verify software and split isolation. Native training and test outcomes remain pending.

### 23 October — task/content v2 native results

- Archived exact lab model/training/test bundle; hashes, splits, frozen inputs and per-row/per-topic metrics reconcile offline. Pair: 59/60 topic-test correct, all 24 redirections reviewed, one clean summary falsely reviewed. Task-only: 48/60; content-only: 36/60.
- Synthetic AI-authored shared-template evidence only; no independent security accuracy or live protection claim. Existing gateway unchanged.
- Prepared 48-case new-wording diagnostic for frozen models, with task-dependent analysis/quotation controls; no retraining. See [v2 report](CONTEXT_V2_PROTOTYPE_REPORT.md) for terminal-3 commands.

### 23 October — context v2 wording transfer exposes weak generalization

- Exact uploaded result reconciles with frozen models, checkpoint, inputs and 0.5 cutoff. Pair: 35/48 correct, 4/16 redirections reviewed, 12 missed, one false review among 32 allowed. Task/content-only: 32/48, zero redirections reviewed.
- Earlier shared-template topic-test success does not establish wording robustness. Keep v2 offline; broaden development data, split by template family and reserve independently reviewed tests before a separately versioned candidate.
- See [transfer report](CONTEXT_V2_WORDING_TRANSFER_REPORT.md); no live gateway changes.

### 23 October — external dataset intake prepared

- Added a standard-library, metadata-only audit for LLMail-Inject (Hugging Face), its companion analysis repository and Tensor Trust. Exact revisions, cards, listings, license documents and digests precede any payload ingestion or training. Cloud Hugging Face access is denied; run audit on the lab host.
- See [intake protocol](EXTERNAL_DATASET_AUDIT_PROTOCOL.md) for terminal-3 commands and audit archive upload. Existing models and servers unchanged.

### 23 October — external audit verified; LLMail Phase 1 intake prepared

- Uploaded document byte counts and SHA256 digests reconcile. LLMail dataset card declares MIT; Tensor Trust license remains unresolved. Two GitHub listings were rate-limited despite overall audit completion.
- Pinned downloader preserves Phase 1 raw grouping metadata, source annotations and scenario/benign support files. Phase 2 remains untouched. No training or classifier labels assigned; payloads stay local and are Git-ignored.
- See [audit report](EXTERNAL_DATASET_AUDIT_REPORT.md) for terminal-3 intake and summary upload.

### 23 October — LLMail intake completed; grouping audit prepared

- Preserved operator intake summary: eight files, no errors, publisher row counts matched. 127,376 True, 9,452 False, 23,911 Unclear and two malformed annotation values; automated provenance remains explicit.
- Added local hash verification, exact text-to-raw join statistics and connected-team analysis over shared raw texts. No split, near-duplicate guarantee, binary relabeling or training. See [intake report](LLMAIL_PHASE1_INTAKE_REPORT.md).

### 23 October — grouping evidence and Boolean-label parser correction

- Preserved original group audit: 160,734/160,741 annotation texts matched; 142 components across 224 teams, largest 78. Counts and intake hash references reconcile.
- Operator type inspection shows 1,399 Boolean True values, one numeric and one list. Corrected parser accepts JSON booleans and exact label strings without coercing numerics. Expected normalized positives 127,376; malformed two, not 1,401. Original result retained unchanged.
- Fresh groups_v2 run adds per-component normalized-label counts and persisted team mapping to assess split feasibility. No training/split/Phase 2 use. See [group audit report](LLMAIL_GROUP_AUDIT_REPORT.md).

### 23 October — corrected groups verified; fixed Phase 1 projection split

- Corrected source/label totals, component sums and grouping script checksum reconcile. Preserved full corrected summary.
- Fixed whole-component 70/15/15 target-deficit assignment yields 101,749/17,537/17,536 definite-label texts, preserving shared exact text within one split. Near-duplicate/template independence remains unresolved.
- Local export uses observed scenario legitimate user_query with one unchanged annotated email; source automated labels/projection limitations explicit. No GPU/fitting/Phase 2/benign-FP consumption. See [preparation protocol](LLMAIL_PREPARATION_PROTOCOL.md).

### 23 October — Phase 1 export reconciled; readiness checks prepared

- Uploaded export summary matches fixed split and exporter source digests; all source-label/reason/exclusion counts reconcile. Large file digests remain operator-reported.
- Added cached CPU-tokenizer length measurements and capped, explicitly approximate lexical overlap screening across splits. No reserved model scores or fitting. See [readiness protocol](LLMAIL_READINESS_PROTOCOL.md).

### 23 October — readiness reveals long-input and leakage gaps

- Retained exact uploaded summary and reconciled source/preparation digests. Train/validation/test long-email counts: 59,924/6,434/3,547. Initial lexical screening detected 872 pairs but exhausted two-million budget and skipped overfull queries. Not a clean leakage result.
- Prepared explicitly selective short-email baseline with no truncation, exhaustive normalized exact-key cleanup and approximate MinHash candidates. Candidate overflow is handled by conservative lower-priority exclusion, not skipped comparisons. Source-label, coverage and approximate-search limitations retained. No fitting/GPU work.

### 23 October — cleaned short subset verified; actual baseline training ready

- Retained uploaded cleanup evidence and reconciled digests/counts. 3,896 train, 1,892 validation, 13,989 reserved test; 47,140 conservative removals are not all verified duplicates. Development distribution heavily selected and negatives scarce.
- Prepared pair/task-only/content-only CPU XGBoost heads on pinned CUDA/FP16 MiniLM embeddings; fixed weights/parameters/cutoff, always-positive comparator, imbalance-aware validation metrics. Test file hashed but not parsed/encoded/scored. No integration or serving changes.
- See [training protocol](LLMAIL_SHORT_TRAINING_PROTOCOL.md) for terminal-3 training and small model archive upload.

### 23 October — first external-data model results verified

- Archived exact three-head training bundle; source/artifact hashes, development IDs, class counts and per-observation metrics reconcile. Pair validation balanced accuracy 55.42%, 34/40 source negatives flagged; content-only 56.78%, 33/40 flagged. No demonstrated pair benefit or acceptable false-alarm rate; keep offline.
- Prepared frozen-head diagnostic on publisher benign emails, preserving fixed cutoff and reporting length/development-overlap exclusions. No reserved test file opened and no retraining. See [training report](LLMAIL_SHORT_TRAINING_REPORT.md).

### 23 October — benign flags verified; validation-only cutoff policy frozen

- Reconciled exact uploaded benign result: 160 eligible unique emails, 43 duplicates excluded. At 0.5, pair flags 20 (12.5%), content-only 8 (5%), task-only 160. Not independent human-reviewed production rates.
- Frozen validation-negative-only cutoff rule (<=4/40 flags, cutoff >=0.5) yields pair recall 79.86%/specificity 90%, content-only 76.73%/90%; task-only recall 0.22%. Reused benign scores show zero flags at higher cutoffs, not independent confirmation.
- Prepared one reserved short-email run reporting both cutoffs/all heads without fitting. Test remains unscored pending lab run. See [benign/cutoff report](LLMAIL_BENIGN_AND_CUTOFF_REPORT.md).

### 23 October — reserved short test complete; operating point does not transfer

- Archived full reserved result; frozen source/policy/model/scorer digests, IDs/labels and per-probability metrics reconcile. Float aggregate comparisons tolerate 1e-12 reduction roundoff; counts exact.
- Pair adjusted cutoff: 8,181/13,282 source positives flagged, 165/707 source negatives flagged (balanced accuracy 69.13%). Content-only: 7,233 positives, 141 negatives (67.26%). Empirical validation negative-flag target did not transfer.
- Keep candidate offline and original/adjusted results together. Prepared blinded 80-case validation-only label review; no reserved text used for selecting the packet and no additional fitting. See [reserved test report](LLMAIL_RESERVED_TEST_REPORT.md).

### 23 October — blinded packet AI review completed

- Reviewed 80 uploaded validation cases: 24 benign-for-injection, 42 injection, 14 unclear. Every ID/task/email preserved exactly; AI-only reviewer provenance and individual reasons recorded. No source mapping/model probabilities consulted for labels; prior aggregate findings known.
- Inert decoding distinguishes an ASCII85 instruction from a Base64 poem; no encoded instructions executed. Ambiguous recipient intent remains unclear.
- Prepared local source-versus-review comparison without refitting or modifying publisher labels. See [review report](LLMAIL_AI_LABEL_REVIEW.md).

### 23 October — review comparison verified; diagnostic score reuse complete

- Preserved uploaded source/AI cross-tab and verified 80 labels/provenance against frozen review manifest and source hashes. Eleven source negatives disagree as AI injection; 14 cases remain unclear. These are not proven source errors.
- Joined original blinded text hashes to saved validation probabilities locally in cloud; no lab/GPU rerun needed. Pair source-negative flags: 19 AI benign, 11 AI injection, four unclear. Post-hoc AI-clear rescoring remains diagnostic, not held-out accuracy.
- Provided blinded 25-case priority adjudication packet for an independent reviewer. No label overwrite, refit, threshold change or serving change. See [alignment diagnostic](LLMAIL_LABEL_ALIGNMENT_DIAGNOSTIC.md).
