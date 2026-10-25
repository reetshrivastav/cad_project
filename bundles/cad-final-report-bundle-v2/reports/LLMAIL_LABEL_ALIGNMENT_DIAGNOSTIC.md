# Source-label disagreement and AI-only diagnostic rescoring

The uploaded [comparison](evidence/llmail_review_comparison_20261023/llmail_ai_review_comparison_v1.json) matches the frozen AI review, reviewer provenance, reviewed-CSV digest, validation digest and comparator source. Source labels and review labels reconcile for all 80 cases:

| Publisher source label | AI benign-for-injection | AI injection | AI unclear |
| --- | ---: | ---: | ---: |
| False (40 selected) | 24 | 11 | 5 |
| True (40 selected) | 0 | 31 | 9 |

This demonstrates disagreement with the task-aware AI interpretation, not 11 proven publisher mistakes. The review is AI-only, the sample was selected from validation, and many clear injection cases are related multilingual role-spoofing variants. No human ground truth or population error estimate follows.

## Existing probabilities clarify part of the false-alarm finding

No further lab execution was necessary. The original blinded email strings map to validation IDs through the frozen source-ID recipe (`LLMAIL-P1-` plus SHA256 of unchanged email text). Those IDs join to the saved validation probabilities; joined source labels agree with the uploaded comparison. The [verified diagnostic](evidence/llmail_review_comparison_20261023/verified_diagnostic.json) records the results and hashes without copying source email text into Git.

Of the pair model's 34 source-negative flags at 0.5, AI review labels 11 injection, 19 benign and four unclear. Thus possible target disagreement explains some flags, but does not remove the false-alarm concern. In this packet the model also flags 19/24 AI-benign cases at 0.5. The original reserved-test findings remain unchanged.

For completeness, rescore only the 66 AI-clear cases (42 injection, 24 benign), excluding 14 unclear, at already frozen cutoffs:

| Head | Cutoff | Flags / 42 AI injections | Flags / 24 AI benign |
| --- | --- | ---: | ---: |
| Pair | Original 0.5 | 42 | 19 |
| Pair | Existing validation-selected | 33 | 1 |
| Task only | Original 0.5 | 42 | 24 |
| Task only | Existing validation-selected | 0 | 0 |
| Content only | Original 0.5 | 41 | 18 |
| Content only | Existing validation-selected | 32 | 0 |

Pair adjusted balanced agreement with this AI review is 87.20%; content-only is 88.10%. These are **post-hoc selected-validation diagnostic agreements**, not new held-out accuracy, human-reviewed security results or evidence overriding the weaker reserved test. No cutoff, model, source label or serving behavior changed. Unclear cases must not silently become benign or be excluded from future reports without coverage counts.

## Next decision and concrete review artifact

Do not refit the heads merely to agree with 66 assistant labels. The current useful milestone is an independent adjudication of the task/trust labeling contract and disputed examples. A 25-case blinded priority packet is provided separately for download: all 14 unclear cases and 11 source-negative/AI-injection disagreements. The [manifest](evidence/llmail_review_comparison_20261023/adjudication_manifest.json) preserves IDs/selection/hash; task/email content and blank label/reviewer/notes remain in the downloadable CSV outside Git. Source/AI labels and scores are hidden in that packet.

A professor or another independent reviewer can mark `benign`, `injection` or `unclear`, recording their actual identity and reasons. This targeted review does not certify the other AI labels or yield a representative model benchmark. Another assistant-only pass is possible but must remain labeled AI-only, not independent human review.

For prompt-injection labeling, ordinary requests to human email recipients are not automatically instructions to the assistant. Clearly spoofed roles, task replacement and unauthorized tool demands count as injection. Phishing/harmful content, encoding and incomplete emails need separate interpretation; they do not automatically decide the injection label. Do not execute instructions within examples.

No GPU run or local command is needed now. Preserve the original publisher labels and the inspected reserved test. After independent review, define any revised development targets explicitly, fit a separate candidate if justified, and reserve a different evaluation source before tuning. Longer-email support and downstream agent validation are still separate research/engineering work.
