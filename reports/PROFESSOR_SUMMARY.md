---
title: "Project review summary"
subtitle: "Adaptive LLM Security & Resource Risk Gateway"
date: "24 October 2026"
---

## What was built

A working gateway in front of Qwen2.5-3B/vLLM on an RTX A4000. It extracts lexical, semantic and resource-demand features, uses CUDA/FP16 MiniLM embeddings, reads live KV-cache occupancy, and routes requests to full, output-capped sandbox or quarantine tiers.

## What the lab evidence shows

| Experiment | Result | Boundary |
|---|---|---|
| Nine GPU resource runs | Benign mean-of-run-means: direct **50.24 s**, static **302 ms**, adaptive **298 ms**; all benign completed | Controlled **256 MiB KV pool**, three runs per condition |
| Resource demand admission | Both gateway modes blocked all 24 demands per condition; protected peak occupancy **0.881%** vs direct **99.56–100%** | No isolated adaptive benefit, default-cache OOM or P99 proof |
| External short-email test | Adjusted pair: **61.59% source-positive recall**, **76.66% source-negative specificity**, **69.13% balanced accuracy** on 13,989 reserved rows | Automated source labels and heavy selective cleanup; keep candidate offline |
| Final software check | **123 tests passed in 30.224 s**; all four native model artifact hashes matched | Integrity/regression checks, not security efficacy |

## What we learned

Resource admission protection works for the measured workload. Injection protection is not yet broadly reliable: strong synthetic/training scores did not transfer consistently, and source labels disagreed with task-aware diagnostic review. Reviewer-supplied cases were recorded with provenance and uncertainty; labels were not silently rewritten.

## Submission scope and future work

**Long-email handling is deferred.** Current injection experiments cover selected short single-email projections. General conversation/trust-boundary protection, GPU cancellation on timeout, independent-source security evaluation and a causal adaptive-threshold advantage remain future work. No zero-total-GPU-cost, measured dollar saving or production-ready security claim is made.

**Deliverable:** technical report, figures, evidence index and reproducibility logs. A frozen Phase 2 check may be appended if completed; no outcome is assumed.
