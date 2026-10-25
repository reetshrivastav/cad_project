# Current project status — 25 October 2026

**Final evidence edition 2.0 is ready.** Start at the [report/evidence index](README.md) or [complete report](FINAL_PROJECT_REPORT.md).

- Controlled GPU protection: nine runs; benign mean direct 50.24 s, static 302 ms, adaptive 298 ms. Constrained 256 MiB cache; no isolated adaptive advantage or default-cache OOM proof.
- Native serving: CUDA/FP16 MiniLM, Qwen/vLLM, full/sandbox/quarantine, fresh telemetry. Live checks passed.
- Tuning: opt-in direct inference preserved 39 checked feature/risk/tier cases. Live extraction 24.62 to 18.84 ms in separate ten-probe checks. Sub-5-ms target remains unmet; original path stays default.
- LLMail reserved short pair: adjusted recall 61.59%, specificity 76.66%, balanced accuracy 69.13%; keep experimental head offline.
- Long emails: 300 emails/723 windows fully covered offline; max aggregation flags most negatives. Coverage is not reliable semantic protection.
- Phase 2 content-only: 2,000 source-labeled emails, adjusted recall 53.92%, specificity 84.26%, balanced accuracy 69.09%. Same-challenge transfer; no inferred trusted task, no pair/task evaluation.
- Integrity: 135 lab tests in 4.609 s and four native hashes matched. Later optimized code passed 138 cloud CPU tests, plus lab parity/live checks.

The bounded study is complete enough for documentation. Further work includes contextual injection robustness, independently reviewed/fresh-source evaluation, GPU cancellation, causal adaptation benefit, broader latency engineering and dedicated novelty/prior-art analysis. Training accuracy, simulation dollars and architectural targets are not independent experimental claims.
