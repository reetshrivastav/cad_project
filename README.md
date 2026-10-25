# Adaptive LLM Security & Resource Risk Gateway

A research prototype that screens LLM requests using lexical, semantic and resource-demand features, then assigns full, output-capped sandbox or quarantine admission. The native gateway runs CUDA/FP16 MiniLM and forwards admitted requests to Qwen2.5-3B-Instruct through vLLM. Live KV-cache telemetry can tighten thresholds.

**Start here: [Reports, findings and evidence](reports/README.md).**

## Final deliverables — 25 October 2026, edition 2.0

- [Complete technical report](reports/FINAL_PROJECT_REPORT.md).
- [PDF, editable Word, professor summary and figures](reports/final_report/README.md).
- [Current status](reports/CURRENT_STATUS.md).
- [Evidence paths and SHA256 digests](reports/final_report/EVIDENCE_INDEX.csv).
- [All scripts and test modules](reports/SCRIPT_TEST_INDEX.md).

For PDF/Word on GitHub, open the file and select **Download raw file**. The Markdown reports can be read directly in the browser.

## Measured findings

| Evaluation | Observation | Scope |
|---|---|---|
| Nine GPU demand-burst runs | Benign mean: direct 50.24 s; static 302 ms; adaptive 298 ms | Three runs per condition, controlled 256 MiB KV pool |
| Admission protection | 24/24 demands blocked per protected condition; all 24 benign probes completed | Tested capped generation workload, not default-cache OOM |
| KV occupancy | Direct 99.56–100%; protected 0.881% | Active cache blocks, not total device allocation |
| Reserved short-email pair model | Adjusted recall 61.59%, specificity 76.66%, balanced accuracy 69.13% | 13,989 selectively retained publisher-labeled rows; offline |
| Long-email extension | 300 emails, 723 windows completely covered | Detection discrimination remains weak |
| Phase 2 content-only transfer | Adjusted recall 53.92%, specificity 84.26% | 2,000 short emails, related challenge, offline |
| Opt-in inference tuning | Mean live extraction 24.62 to 18.84 ms; 39 parity cases matched | Separate small smoke tests; sub-5-ms target unmet |

The study supports controlled resource admission protection. General prompt-injection prevention, a causal advantage from adaptation, GPU cancellation at timeout, population P99, measured dollar/energy savings and patent novelty are **not established**. Native training accuracy is resubstitution, not held-out security accuracy. Quarantine avoids backend forwarding but still incurs CUDA ingress work.

## Lab demonstration

The existing lab uses separate `.venv` gateway and `.venv-vllm` backend environments. Preserve that separation; do not install backend dependencies into the gateway environment. The supplied launchers use lab-native artifacts in `models/lab_native_v1` and a constrained cache configuration matching the controlled study. Those operator-generated artifacts/source datasets are not all distributed at their lab paths.

Terminal 1:

```bash
cd ~/cad_project
bash scripts/start_lab_vllm.sh
```

After vLLM is ready, terminal 2:

```bash
cd ~/cad_project
GATEWAY_EMBEDDING_MODE=direct \
bash scripts/start_lab_gateway.sh adaptive
```

`direct` is opt-in; omitting the variable uses the original `encode` path. Use `static` instead of `adaptive` for the static threshold control. Experimental LLMail/context heads remain offline and must not replace the native model silently.

After gateway readiness, terminal 3:

```bash
cd ~/cad_project
.venv/bin/python scripts/check_live_gateway.py \
  --output results/live_demo_new.json
```

Readiness: `http://127.0.0.1:5000/api/status`; telemetry: `http://127.0.0.1:5000/api/pressure`. Use fresh output names to preserve evidence.

## Verification

With both servers stopped:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/verify_native_artifacts.py \
  --model-dir models/lab_native_v1
```

The current cloud suite passes 138 CPU tests. The final supplied lab regression passed 135 tests before the optional inference path was added; later lab parity/live checks passed. These checks have different scopes and are not a replacement for physical GPU replication.

## Repository map

| Location | Purpose |
|---|---|
| `app.py`, `router.py`, `cache_pressure.py`, `embedding_runtime.py` | Live gateway, pressure-aware policy and optional inference path |
| `classifier.py`, `features.py`, training/simulation modules | Native model utilities and historical simulation |
| `context_pair_v2.py`, `llmail_*.py` | Separate offline research helpers; frozen evidence dependencies |
| `scripts/` | Launchers, datasets, experiments, analyzers and rendering |
| `tests/` | CPU behavior and preserved-evidence checks |
| `reports/` | Technical reports, protocols, historical evidence and final documents |
| `results/final_validation_20261025/` | Final unchanged lab uploads and source hashes |
| `data/external/`, lab-native model directories | Large/operator-generated local artifacts; follow protocols |

Historical architecture guides, simulation summaries and patent drafts are retained for provenance. Their aspirational numbers and claims do not supersede the measured final report. AI-assisted labeling is disclosed separately from reviewer judgments; source annotations and failed/negative results are preserved.
