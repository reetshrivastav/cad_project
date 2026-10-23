# Current lab evidence — 23 October 2026

The GPU-backed resource-risk gateway works. General prompt-injection protection is still experimental. This page summarizes measured native-lab outcomes; older project documents also contain design goals, training-set numbers and simulations that must not be presented as current independent evaluation.

| Area | Observed evidence | Important boundary |
| --- | --- | --- |
| GPU inference | Qwen2.5-3B-Instruct through vLLM; MiniLM CUDA/FP16 ingress | Consistent sub-2 ms embedding/sub-5 ms live ingress not established |
| Admission protection | Nine controlled runs: direct benign mean 50.24 s, static 302.00 ms, adaptive 298.05 ms; all benign completed | Constrained 256 MiB KV pool, capped synthetic generation; not default-cache/OOM proof |
| Adaptive benefit | Both gateway modes block all tested high-demand requests | Incremental benefit from threshold tightening not established |
| Sandbox | Live request capped at 256 output tokens; backend counters match | Five-second HTTP read timeout does not prove GPU cancellation |
| Native benign scoring | Four quarantines and nine sandbox cases among 200 AI-labeled benign prompts | Same-source screened sample, AI-only labels; not independent human ground truth |
| Native controlled injection scoring | 1/75 quarantine, 2/75 sandbox, 72/75 full | Source-derived constructed contexts, not downstream ASR |
| Specialized shadow detector | 75/75 attack flags, 0/200 AI-labeled benign flags, but clean memo also flagged | Shared-wrapper false alarm prevents calling this perfect detection; not integrated |
| Matched wrapper follow-up | Guard or tags trigger harmless controls; neither clears controls but flags only 1/75 attacks | Sensitivity diagnosed on fixed development cases, not a security fix |

Native classifier 98.24% is **training-set resubstitution accuracy**, not held-out accuracy. GPU ingress itself uses CUDA, so quarantine is not zero total GPU work. Avoided backend tokens were measured for the controlled stress workload; GPU dollars, zero-VRAM deltas and zero-FLOP claims were not established.

The next injection revision needs a task/trust-aware input and labeling contract, group-separated training/validation and a fresh untouched test corpus. Already-inspected cases can be diagnostics/regressions but cannot become fresh held-out evidence after tuning. Conversation/session robustness and real cancellation remain separate engineering work. No live detector or weights were changed during the diagnostic reports.

An [offline task/content v2 prototype](CONTEXT_V2_PROTOTYPE_PROTOCOL.md) is now prepared. Its 400 synthetic contrast cases are split by topic (280/60/60), with pair/task-only/content-only models and separate test scoring. This supplies a development sanity check, not independent human-labeled/novel-template security validation. Native results are now verified: pair 59/60 correct, task-only 48/60 and content-only 36/60 on six synthetic test topics. The pair model reviewed all 24 redirections and falsely reviewed one of 36 allowed cases. See [v2 report](CONTEXT_V2_PROTOTYPE_REPORT.md). The subsequent [48-case wording-transfer diagnostic](CONTEXT_V2_WORDING_TRANSFER_REPORT.md) exposed poor transfer: pair reviewed only 4/16 redirections, missed 12 and falsely reviewed 1/32 allowed cases (35/48 correct). Both single-input baselines reviewed zero redirections. Keep v2 offline; next work is broader family-separated data and independently reviewed reserved tests. Serving remains unchanged.

Primary reports: [GPU replications](GPU_REPLICATION_REPORT.md), [sandbox](SANDBOX_VALIDATION_REPORT.md), [benign scoring](BENIGN_AI_LABELED_EVALUATION_REPORT.md), [controlled injection scoring](BIPIA_CONTROLLED_EVALUATION_REPORT.md), [shadow detector](INJECTION_CANDIDATE_DIAGNOSTIC_REPORT.md), [matched wrappers](WRAPPER_DIAGNOSTIC_REPORT.md).

Current cloud regression verification: 117 CPU tests passed. Actual GPU outcomes are operator-supplied, preserved and reconciled in the linked reports; CPU test success does not establish injection efficacy.

[External metadata audit verified](EXTERNAL_DATASET_AUDIT_REPORT.md): LLMail card declares MIT; Tensor Trust license remains unresolved. [Phase 1 intake completed](LLMAIL_PHASE1_INTAKE_REPORT.md): 370,724 raw rows, 224 teams, 160,741 annotations, 203 benign emails. [Original grouping audit](LLMAIL_GROUP_AUDIT_REPORT.md) matched 160,734/160,741 annotation texts; 224 teams form 142 exact-sharing components (largest: 78 teams). A parser correction accepts 1,399 Boolean positives previously counted as malformed; corrected component counts reconcile. A [fixed split and local projection export](LLMAIL_PREPARATION_PROTOCOL.md) are prepared: 101,749 training, 17,537 validation and 17,536 reserved test source-labeled texts. No near-duplicate independence or human ground truth is implied. Phase 2 remains untouched; the later short-only training run is summarized below.

[Phase 1 export verified; readiness check prepared](LLMAIL_READINESS_PROTOCOL.md): 136,822 source-labeled projections, with long emails requiring explicit token-window handling. Token-length measurement and bounded screening were completed; findings and subsequent short-only training are summarized below.

[Readiness result](LLMAIL_SHORT_BASELINE_PROTOCOL.md): 59,924/101,749 training emails exceed 256 tokens; initial lexical screen detected 872 cross-split pairs but exhausted its budget. Preparation of a no-truncation short-email subset with complete normalized exact-key cleanup and broader approximate MinHash screening is now available. Full-length email support remains unresolved; the short-only candidate remains offline.

[Short baseline cleanup reconciled; training protocol prepared](LLMAIL_SHORT_TRAINING_PROTOCOL.md): retained 3,896 training (248 source negatives), 1,892 validation (40 negatives), 13,989 reserved test rows. Aggressive conservative cleanup removed 70.45% of eligible short rows; these are not all confirmed duplicates. First fixed class-balanced offline training has completed; its weak validation results are summarized below.

[LLMail training evidence verified](LLMAIL_SHORT_TRAINING_REPORT.md): pair validation balanced accuracy 55.42%, 34/40 source negatives flagged; content-only 56.78%, 33/40 flagged. Keep models offline. Next frozen-head diagnostic uses the separate publisher benign collection with explicit short-input/overlap exclusions; reserved Phase 1 test remains unscored.

[Benign diagnostic verified; cutoffs frozen for reserved scoring](LLMAIL_BENIGN_AND_CUTOFF_REPORT.md): 43 duplicate occurrences excluded from 203 publisher emails; flags among 160 eligible uniques: pair 20, content-only 8, task-only 160. A validation-negative-only cutoff rule now trades recall for at least 90% empirical validation specificity; pair recall 79.86%, content-only 76.73%. Benign rechecks are reused diagnostic evidence. The reserved short test is now completed and summarized below; no refit occurred.

[Reserved short-email test verified](LLMAIL_RESERVED_TEST_REPORT.md): pair adjusted recall 61.59%, specificity 76.66%, balanced accuracy 69.13%; content-only 54.46%/80.06%/67.26%. Validation 10% negative-flag target did not transfer. Candidate stays offline. This test is now inspected; no retuning can make it fresh. Next is a blinded development-label audit, not another GPU rerun or deployment.
