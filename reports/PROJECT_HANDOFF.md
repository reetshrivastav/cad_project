# Project handoff — 24 October 2026

The project has a working GPU-backed admission gateway and a documented controlled resource-protection result. The injection work has produced reproducible experiments and exposed generalization/labeling weaknesses; it has not produced a broadly reliable injection defense. Preserve both outcomes in presentations and papers.

## Completed evidence package

| Deliverable | Measured outcome | Scope |
| --- | --- | --- |
| Qwen/vLLM integration | GPU inference, routed full/sandbox requests, quarantine and live KV telemetry | RTX A4000 lab; gateway remains on its existing native model |
| Controlled resource stress | Three blocks × direct/static/adaptive; benign run-mean averages 50.24 s / 302 ms / 298 ms, all benign completed | Deliberately constrained 256 MiB KV pool; no full-default-cache OOM or P99 claim |
| Sandbox output control | Live request capped at 256 output tokens with backend counter reconciliation | HTTP read timeout does not prove GPU cancellation |
| Context-aware synthetic prototype | 59/60 topic-test correct; new wording reviewed only 4/16 redirections | Negative transfer finding retained |
| External LLMail baseline | 13,989 reserved short rows; adjusted pair positive recall 61.59%, negative specificity 76.66%, balanced accuracy 69.13% | Publisher source annotations, substantial selective cleanup; not human ground-truth accuracy |
| Benign diagnostic | Pair flags 20/160 and content-only 8/160 unique publisher benign emails at 0.5 | Same-source diagnostic, not fresh after tuning |
| Label-policy review | AI/source disagreements and targeted reviewer-supplied judgments recorded separately | No automatic source-label rewriting or refit |

Core evidence: [GPU replications](GPU_REPLICATION_REPORT.md), [reserved short test](LLMAIL_RESERVED_TEST_REPORT.md), [label alignment diagnostic](LLMAIL_LABEL_ALIGNMENT_DIAGNOSTIC.md). Earlier source documents contain design targets and historical training/simulation numbers; they must not override measured limitations in these reports.

## Corrected reviewer packet: cycle closed

The latest upload supplies 13 injection, six benign and six unclear labels under reviewer `Reet`. Twenty-four rows preserve the original task/email exactly: 13 injection, six benign, five unclear. Row `LLMAIL-REVIEW-042` replaces the original garbled content with a corrupted-source placeholder. Exclude that row from original-text judgments rather than ask for another encoding repair. The review cycle closes with that explicit exclusion; no more CSV rechecks are required.

The [verified review](evidence/llmail_human_review_corrected_20261024/verified_review.json) preserves supplied labels/notes, hashes, input-integrity exclusion and post-hoc comparison with saved validation scores. Only 19 clear, intact targeted development cases enter that diagnostic; five unclear and one changed-input case do not. This is reviewer-supplied human-labeled development evidence, with prior AI exposure and selection bias, not independent blinded ground truth. It does not replace the original source-labeled reserved test, and it is too small to justify a reliable retrained detector or production-rate claim by itself.

## Fast path to a reviewable prototype submission

1. Freeze the existing models and keep the experimental heads offline. Do not spend more cycles retuning on inspected tests.
2. Run the final local software/artifact checks below and retain their output with the existing reports.
3. Use the measured-outcome table and linked reports for the demonstration/professor handoff. Present the injection findings as limitations and research results, not solved protection.

Terminals 1 and 2 can remain stopped. In terminal 3:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/final_project_check.py \
  --model-dir models/lab_native_v1 \
  --output-dir results/project_handoff_v1
```

Then package the small logs/summary even if a check failed:

```bash
cd ~/cad_project
tar -czf ~/Desktop/cad-project-handoff-v1.tar.gz \
  -C results project_handoff_v1
```

Upload `cad-project-handoff-v1.tar.gz` for reconciliation. These checks require no running servers or new GPU experiment and do not download/install dependencies. Each subprocess has a five-minute timeout. A passing result closes the software reproducibility check for the current prototype; it does not close the unresolved security objectives.

## Remaining requirements for the broader security objective

Prioritize rather than silently expand scope:

1. Reliable injection model: broader, consistently labeled development data and separately reserved source/family evaluation after any refit; inspected tests stay historical evidence. Decide acceptable missed-injection/false-alarm tradeoffs before scoring.
2. Coverage: long-email handling, full-conversation/trust-boundary input contract and state/length budgets. Current offline baseline covers selected short single-email projections.
3. Operational proof: downstream attack-success and legitimate-task completion evaluation; GPU cancellation on deadline; isolated benefit from adaptive thresholds. Default/full-cache pressure testing and broader latency distributions are further evidence gaps.

These items are future implementation/research work if the submission claims broad defense. No prototype report, test-suite pass or targeted reviewer packet establishes production safety, patent novelty or paper acceptance. The current measured resource result and openly reported injection limitations can be handed over now without claiming those objectives complete.
