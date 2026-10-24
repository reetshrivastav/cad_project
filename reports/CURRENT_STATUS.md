# Current project status — 24 October 2026

The GPU resource-risk gateway works and its controlled stress results are documented. General prompt-injection protection remains experimental. [Final report edition 1.1](FINAL_PROJECT_REPORT.md), [PDF/Word package](final_report/README.md) and [professor summary](PROFESSOR_SUMMARY.md) include the completed long-email extension and its quality limitations.

| Area | Current evidence | Boundary |
| --- | --- | --- |
| GPU routing | Qwen2.5-3B/vLLM; CUDA/FP16 MiniLM; full/sandbox/quarantine and live cache telemetry | Consistent ingress-latency targets and complete context robustness not established |
| Admission protection | Nine runs: direct benign mean 50.24 s, static 302 ms, adaptive 298 ms; all benign completed | Controlled 256 MiB pool; no isolated adaptive advantage, P99, default-cache OOM or dollar-saving proof |
| Sandbox | 256-token live output cap reconciled with counters | GPU cancellation on deadline not demonstrated |
| Context v2 | Synthetic topic test 59/60; new wording only 4/16 redirections reviewed | Weak transfer, kept offline |
| LLMail short reserved test | Adjusted pair recall 61.59%, specificity 76.66%, balanced accuracy 69.13%, 13,989 rows | Automated source labels, selective cleanup; not general security accuracy |
| Long-email extension | 300 emails completely covered by 723 windows, 130,735 content-token positions | Offline scoring only; no live long-context defense |
| Long quality | Pair max at 0.5: 274/276 source positives, 22/24 source negatives flagged; higher cutoff 218/276 and 18/24 | High flags/recall do not imply useful discrimination; only 24 source negatives |
| Reviewer packet | 24 intact cases: 13 injection, six benign, five unclear; changed-input row 042 excluded | Targeted development evidence with prior AI exposure, not independent blinded ground truth |
| Phase 2 | Two attempts failed before predictions on unsupported level assumptions; failures preserved | Remaining check is content-only, with no inferred trusted query; not independent-source evaluation |

No experimental head has replaced the native classifier. Source labels and original reserved findings remain unchanged. The long experiment establishes full token coverage for its sample, not semantic understanding, attack localization or downstream prevention. Max pooling amplifies false alarms; mean pooling can dilute instruction signals.

Next lab step: run only the cached [content-only Phase 2 command](LLMAIL_LONG_EMAIL_RESULTS.md). Models/cutoffs/sample rules remain fixed. Do not repeat the long run, retune against inspected tests, or run the obsolete two-job wrapper again.

Software checks: 133 current cloud CPU tests pass. Historical lab handoff passed 123 tests in 30.224 seconds and verified four native artifact hashes without unpickling. Actual GPU results are operator-supplied and reconciled through hashes, intervals and probability/counter analysis; cloud verification does not independently reproduce the lab embeddings.

Native classifier 98.24% is training resubstitution, not held-out accuracy. Quarantine still uses CUDA ingress. Token avoidance is measured for the controlled workload; zero-total-GPU-cost/zero-VRAM/zero-FLOP claims are unsupported. Conversation/trust/session limits, cancellation and fresh independently reviewed/source-separated evaluation remain unresolved. Existing architecture documents include goals and historical simulations; measured reports govern the current claims.
