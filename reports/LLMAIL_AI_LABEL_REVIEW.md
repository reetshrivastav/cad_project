# AI-only blinded validation-label review — 23 October 2026

Reviewed the 80-case packet against its trusted task and untrusted email text: **24 benign-for-injection, 42 injection, 14 unclear**. Reviewer is explicitly `OpenAI assistant (AI-only; no independent human adjudication)`. Original IDs, tasks and email strings were verified unchanged after writing and rereading the completed CSV. Downloadable CSV stays outside Git; the [manifest](evidence/llmail_label_review_ai_20261023/review_manifest.json) retains source/review hashes, per-ID labels and rationales without duplicating source payloads.

Source mapping and model scores were not consulted during labeling, although earlier aggregate experiment findings were known. This is not an independent human review, a representative prevalence estimate or a new model-performance evaluation. The diagnostic sample was deliberately selected from validation (all 40 source negatives and 40 hash-selected positives); label totals alone must not be interpreted as source/model error rates. Source-to-review correspondence is not yet known in the cloud.

The rubric identifies attempts to redirect the summarizer, impersonate user/system roles, alter processing of other messages or cause unauthorized tool actions. Ordinary instructions to an email's human recipient do not automatically constitute prompt injection. `benign` here means no identified prompt injection relative to the stated task; it does not certify the content as harmless, authentic, non-phishing or appropriate to answer.

Many clear cases contain Chinese forged dialogue/role markers and outbound-email instructions. No user authorization can be inferred from dialogue inside untrusted email. Ambiguous recipient-facing payment/action requests are retained as `unclear`, not forced into a binary class. Corrupted/cipher-like or incomplete material also remains unclear when no reliable instruction interpretation was established.

Two inert decoding checks informed individual labels: review 030's ASCII85 text reveals a summarize-then-send directive; review 058's Base64 text yields the Latin O Fortuna poem without a tool/action override. Decoded text was only inspected, never executed. Neither encoding nor a safety claim alone establishes a label.

## Next local comparison — not retraining

Save the supplied completed download as `~/Desktop/llmail-label-review-ai.csv`. Keep its reviewer provenance unchanged. The comparison script reconstructs the exact validation-only packet, verifies IDs/task/email preservation, and reports source-label versus review-label counts without reading the reserved test or fitting anything.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/compare_llmail_label_review.py \
  --data-dir data/external/llmail_short_baseline_v1 \
  --review-csv ~/Desktop/llmail-label-review-ai.csv \
  --output results/llmail_ai_review_comparison_v1.json
cp results/llmail_ai_review_comparison_v1.json ~/Desktop/
```

Upload `llmail_ai_review_comparison_v1.json`. Do not automatically overwrite publisher labels or refit the model on AI labels. An independent reviewer can adjudicate ambiguous/disputed cases using the same blinded rubric; assistant-only labels must never be reported as human ground truth. This remains development evidence, and the already-inspected reserved test cannot become fresh again after label/policy changes.
