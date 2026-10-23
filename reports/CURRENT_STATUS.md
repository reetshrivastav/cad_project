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

An [offline task/content v2 prototype](CONTEXT_V2_PROTOTYPE_PROTOCOL.md) is now prepared. Its 400 synthetic contrast cases are split by topic (280/60/60), with pair/task-only/content-only models and separate test scoring. This supplies a development sanity check, not independent human-labeled/novel-template security validation. Native results are now verified: pair 59/60 correct, task-only 48/60 and content-only 36/60 on six synthetic test topics. The pair model reviewed all 24 redirections and falsely reviewed one of 36 allowed cases. See [v2 report](CONTEXT_V2_PROTOTYPE_REPORT.md). A frozen-model 48-case wording-transfer diagnostic is prepared; serving remains unchanged.

Primary reports: [GPU replications](GPU_REPLICATION_REPORT.md), [sandbox](SANDBOX_VALIDATION_REPORT.md), [benign scoring](BENIGN_AI_LABELED_EVALUATION_REPORT.md), [controlled injection scoring](BIPIA_CONTROLLED_EVALUATION_REPORT.md), [shadow detector](INJECTION_CANDIDATE_DIAGNOSTIC_REPORT.md), [matched wrappers](WRAPPER_DIAGNOSTIC_REPORT.md).

Current cloud regression verification: 82 CPU tests passed. Actual GPU outcomes are operator-supplied, preserved and reconciled in the linked reports; CPU test success does not establish injection efficacy.
