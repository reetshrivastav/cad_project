# Reports and evidence — start here

Current edition: **2.0, 25 October 2026**. The study has completed its bounded evaluation scope. General injection reliability, sub-5-ms ingress, a distinct adaptive advantage and patent novelty are not established.

## Read or download

- [Complete technical report](FINAL_PROJECT_REPORT.md): design, datasets, methods, positive/negative results, tuning, novelty boundaries and limitations.
- [Final PDF](final_report/Adaptive_LLM_Gateway_Final_Report.pdf): download using GitHub's Download raw file button.
- [Editable Word](final_report/Adaptive_LLM_Gateway_Final_Report.docx).
- [Professor summary](PROFESSOR_SUMMARY.md) and [one-page PDF](final_report/Professor_Summary.pdf).
- [Current status](CURRENT_STATUS.md).
- [Machine-readable evidence index](final_report/EVIDENCE_INDEX.csv): paths, hashes, sizes and evidence baselines.
- [Document validation](final_report/document_checks.json): rendering checks, distinct from experiment results.

## Experiment map

| Experiment | Detailed report | Primary evidence / verification |
|---|---|---|
| GPU pilot | [Pilot](GPU_PILOT_REPORT.md) | [Evidence archive directory](evidence/); `scripts/analyze_gpu_pilot.py` |
| Saturation calibration | [Burst](GPU_BURST_REPORT.md) | `scripts/analyze_gpu_burst.py`; capped controlled workload |
| Three-condition, three-block study | [Replications](GPU_REPLICATION_REPORT.md), [protocol](GPU_REPLICATION_PROTOCOL.md) | [Raw runs and derived CSV/plots](evidence/replication_v1_20261021/); `scripts/analyze_gpu_replications.py` |
| Sandbox cap | [Validation](SANDBOX_VALIDATION_REPORT.md) | [Saved cap evidence](evidence/sandbox_validation_20261018/); no demonstrated cancellation |
| Adaptive mechanism | [Calibration](POLICY_CALIBRATION_REPORT.md), [controls](STATIC_ADAPTIVE_CONTROL_REPORT.md) | No measured causal advantage over static protection |
| Benign and BIPIA diagnostics | [Benign](BENIGN_AI_LABELED_EVALUATION_REPORT.md), [BIPIA](BIPIA_CONTROLLED_EVALUATION_REPORT.md) | Source/evaluation scope differs from downstream attack-success rate |
| Specialized model / wrapper bias | [Candidate](INJECTION_CANDIDATE_DIAGNOSTIC_REPORT.md), [wrapper](WRAPPER_DIAGNOSTIC_REPORT.md) | Matched controls expose wrapper sensitivity |
| Synthetic contextual model | [Prototype](CONTEXT_V2_PROTOTYPE_REPORT.md), [wording transfer](CONTEXT_V2_WORDING_TRANSFER_REPORT.md) | Strong topic result, weak redirection transfer; offline |
| External source selection | [Audit](EXTERNAL_DATASET_AUDIT_REPORT.md), [intake](LLMAIL_PHASE1_INTAKE_REPORT.md), [groups](LLMAIL_GROUP_AUDIT_REPORT.md) | Pinned publisher files and diagnostic team components |
| LLMail training and reserved test | [Training](LLMAIL_SHORT_TRAINING_REPORT.md), [reserved](LLMAIL_RESERVED_TEST_REPORT.md) | Frozen heads/cutoffs; extensive documented selection |
| Benign / label disagreement | [Cutoffs](LLMAIL_BENIGN_AND_CUTOFF_REPORT.md), [alignment](LLMAIL_LABEL_ALIGNMENT_DIAGNOSTIC.md) | AI/human provenance retained; original labels not overwritten |
| Long emails | [Results](LLMAIL_LONG_EMAIL_RESULTS.md) | [Complete window evidence](evidence/report_extension_20261024/); `scripts/analyze_report_extension.py` |
| Phase 2 content-only | [Final report section](FINAL_PROJECT_REPORT.md#phase-2-content-only-transfer) | [Reconciled metrics](../results/phase2_content_verified.json), [frozen prediction fixture](../tests/fixtures/llmail-phase2-content-v1.tar.gz); `scripts/analyze_llmail_phase2.py` |
| Final regressions / latency tuning | [Final report section](FINAL_PROJECT_REPORT.md#final-latency-investigation-and-opt-in-tuning) | [Unchanged lab uploads and hashes](../results/final_validation_20261025/); 135 lab regressions, 138 later cloud tests, 39 lab parity cases |

[Complete script and test inventory](SCRIPT_TEST_INDEX.md) links every Python script and test module.

## Repository organization

- Root Python modules implement serving, routing, models and frozen research helpers.
- `scripts/` contains launchers, offline preparation/training, lab experiments and evidence analyzers.
- `tests/` contains CPU regression/evidence tests; fixtures retain bounded prediction evidence without raw email bodies.
- `reports/evidence/` preserves historical experiment evidence at existing paths.
- `results/final_validation_20261025/` preserves the latest operator uploads, including original/optimized live checks.
- `reports/final_report/` contains publication files, figures and evidence index.
- Lab-local `data/external/` contains large source datasets; those files are not distributed in this bundle.

Historical documents are retained for provenance. Current measured claims are governed by edition 2.0, not original roadmap promises. Reorganizing through this index avoids breaking frozen analyzers or lab paths.

## Check or demonstrate

CPU tests, using the gateway environment and with servers stopped:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/verify_native_artifacts.py --model-dir models/lab_native_v1
```

Live demonstration uses three terminals. Terminal 1 runs `bash scripts/start_lab_vllm.sh`; terminal 2, after backend readiness, runs `GATEWAY_EMBEDDING_MODE=direct bash scripts/start_lab_gateway.sh adaptive`. Terminal 3 runs `.venv/bin/python scripts/check_live_gateway.py --output results/demo_new.json`. Choose a new filename to preserve results. Default embedding mode remains `encode` if the environment setting is omitted.

Tests establish software behavior and evidence consistency; they are not a replacement for GPU experiments, security accuracy or an independent replication. Old outputs are historical observations, not promises for another machine.
