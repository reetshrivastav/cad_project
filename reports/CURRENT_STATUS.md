# Current project status — 24 October 2026

The GPU resource-risk gateway works and its controlled stress results are documented. General prompt-injection protection remains experimental. The [project handoff](PROJECT_HANDOFF.md) consolidates completed evidence, a final local verification command and the remaining security requirements.

| Area | Current result | Boundary |
| --- | --- | --- |
| GPU routing | Qwen2.5-3B through vLLM; MiniLM CUDA/FP16; full/sandbox/quarantine and cache telemetry | Consistent sub-2 ms embeddings/sub-5 ms live ingress not established |
| Admission protection | Nine runs: benign mean-of-run-means direct 50.24 s, static 302 ms, adaptive 298 ms; all benign completed | Constrained 256 MiB KV pool; no incremental adaptive benefit, P99, full-cache OOM or dollar-saving proof |
| Sandbox | 256-token output cap verified live | Backend GPU cancellation not demonstrated |
| Context v2 | 59/60 synthetic topic-test correct, but new wording reviewed only 4/16 redirections | Keep offline; template transfer weak |
| External LLMail short baseline | Adjusted pair test recall 61.59%, specificity 76.66%, balanced accuracy 69.13% on 13,989 source-labeled rows | Source automated labels, aggressive selective cleanup, short-only one-email projections; not general defense |
| Publisher benign diagnostic | At 0.5: pair flags 20/160, content-only 8/160, task-only 160/160 | Same-source previously inspected diagnostic |
| Source/AI label audit | 80 selected validation cases expose disagreement and uncertainty | AI review is not independent human ground truth |
| Reviewer-supplied priority audit | 24 intact cases: 13 injection, six benign, five unclear; one changed-input row excluded | Prior AI exposure and targeted selection; not fresh independent evaluation |

No experimental head has replaced the gateway native classifier. No source labels were overwritten. Inspected reserved results remain frozen and cannot become fresh tests after further tuning. Phase 2 remains unused; its suitability as an external test still depends on overlap checks. Long-input, conversation/trust boundaries and downstream agent protection remain unresolved.

Native classifier 98.24% is training resubstitution, not held-out accuracy. Quarantine still uses CUDA ingress work. Backend-token avoidance is measured only for the controlled resource workload; zero-GPU-cost/zero-VRAM/zero-FLOP claims are unsupported. Older architecture documents also contain targets and historical simulations.

Final lab handoff verification passed at source `e037df8`: 123 tests in 30.224 seconds, plus all four native artifact digests matching retained evidence without unpickling. See [final verified summary](evidence/project_handoff_20261024/verified_summary.json). Cloud CPU regression verification also passed 123 tests. Actual GPU outcomes are operator-supplied and reconciled through hashes and probability/counter analysis; CPU tests do not independently reproduce lab inference or establish efficacy.

Primary reports: [GPU replications](GPU_REPLICATION_REPORT.md), [sandbox](SANDBOX_VALIDATION_REPORT.md), [context transfer](CONTEXT_V2_WORDING_TRANSFER_REPORT.md), [external reserved test](LLMAIL_RESERVED_TEST_REPORT.md), [label alignment](LLMAIL_LABEL_ALIGNMENT_DIAGNOSTIC.md), [handoff and final local checks](PROJECT_HANDOFF.md).

Final report package: [technical report](FINAL_PROJECT_REPORT.md), [professor summary](PROFESSOR_SUMMARY.md), PDF/DOCX and source-backed figures under `reports/final_report/`. Long-email handling explicitly deferred. An additional [bounded Phase 2 transfer protocol](LLMAIL_PHASE2_TRANSFER_PROTOCOL.md) is ready; no Phase 2 outcome is included until supplied and verified. New Phase 2 runner software checks bring current cloud suite to 126; historical lab handoff remains 123.

Extension now authorized: [Phase 2 schema repair and full-token long-email window protocol](LLMAIL_LONG_EMAIL_PROTOCOL.md). First Phase 2 run failed before scoring on a suffix assumption; data bytes are cached and preserved. Retry reuses them. A bounded 300-email long-input test compares first/max/mean windows with frozen heads/cutoffs; results pending. Serving unchanged. Cloud software checks now include 130 tests; historical lab handoff remains 123.
