# Long-email extension and Phase 2 parser repair — 24 October 2026

The operator authorized continued testing, including long emails. This extends the short-email evidence edition; no long-email outcome is assumed in the existing report. Keep all heads, source labels and numerical cutoffs unchanged. These are offline evaluations, not deployment of the experimental detector.

## Phase 2 failed schema preflight preserved

The first supplied Phase 2 result failed before predictions with `Unknown Phase 2 level: level1a`. The runner had incorrectly limited suffixes to k–v. The source payloads use an a-suffixed identifier. The task projection depends on the level's numeric retrieval scenario, not the defense suffix. The corrected parser accepts lower-case suffixes for levels 1/2 while preserving the original mapping to retrieval scenarios 3/4, and still checks the Project Zenith/Q2 query strings. Unknown numeric scenarios still fail rather than silently inventing a task.

The [failed result](evidence/llmail_phase2_preflight_20261024/failed_result.json), exact archive and verified summary are retained. It records 68,586,935-byte annotation and 263,506,099-byte raw files with SHA256 digests. There was no model scoring, fitting or cutoff selection. The retry reuses and verifies those exact cached bytes and records observed level counts, keeping the original hash sample/overlap rules. This repairs schema handling, not an unfavorable model outcome.

## Long-email protocol fixed before scoring

Use the original full Phase 1 test projections, not the cleaned short subset. File identity is checked against retained preparation evidence. Previously recorded coverage contains 3,547 long test emails (3,283 source positives, 264 source negatives). No head fit or cutoff selection used these long inputs; source QA and original team-component allocation were already inspected, so this is not an independent-source benchmark.

1. Tokenize without truncation and without special tokens; identify emails whose content plus required specials exceeds 256 tokens. Verify cohort counts against the earlier coverage audit.
2. Sort by SHA256 of `long-email-v1:` plus original ID. Take at most 300 long emails, with no class balancing or model-score-dependent selection.
3. Slide over token IDs directly, with capacity `256 - special_token_count` (254 for this tokenizer) and 32 content tokens of overlap. Pack special tokens without decoding/re-encoding chunks. Every selected email's full token sequence must be covered; do not score only a prefix and call it full coverage.
4. A 20,000-window budget excludes whole emails if needed, with IDs/reasons reported. No partial-email result is allowed. This bounds workload and memory; retained coverage must be reported.
5. Embed each unchanged trusted task and each full token-ID window using the existing pinned CUDA/FP16 MiniLM, in evaluation/inference mode. Apply frozen pair/task-only/content-only heads.
6. Report first-window, maximum-window and mean-window probabilities at both existing cutoff policies. Maximum is the primary coverage-oriented exploratory aggregation; mean and first are prespecified comparisons, not a post-hoc choice of winner. No long-input cutoff tuning or training.

Email-level publisher annotations apply only to the email result. Do **not** label every window an injection: malicious span locations are not supplied. Maximum pooling can multiply false alarms; mean pooling can dilute a localized instruction. A detected tail-score increase is not proof that a malicious span was correctly localized. Coverage of token IDs is not proof of semantic understanding or downstream attack prevention.

## Recommended one-command runner

Keep terminals 1 and 2 stopped. In terminal 3:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/run_report_extension.py
```

This runs both jobs below sequentially and creates `~/Desktop/cad-report-extension-v1.tar.gz`, even if a job fails. Progress remains visible. Each job has a 60-minute timeout; no automatic retraining, resampling or threshold changes occur. Upload the bundle. Existing output directories are preserved rather than overwritten; if the runner reports a prior run, send its result/error before rerunning.

## Individual commands (for transparency; do not also rerun after the runner)

Keep terminals 1 and 2 stopped. Use existing dependencies and cached models. Phase 2 retry needs no new data download; the long test uses existing full-test files. Both require GPU embeddings but no vLLM backend generation or retraining. Run sequentially so each process releases its GPU memory.

**A. Retry Phase 2 with cached payloads**

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/evaluate_llmail_phase2.py \
  --source-dir data/external/llmail_phase1_v1 \
  --group-dir data/external/llmail_phase1_groups_v2 \
  --models-dir models/llmail_short_baseline_v1 \
  --phase2-source-dir data/external/llmail_phase2_transfer_v1 \
  --output-dir data/external/llmail_phase2_transfer_v2
```

**B. Run bounded complete-window long-email evaluation**

```bash
cd ~/cad_project
.venv/bin/python scripts/evaluate_llmail_long.py \
  --prepared-dir data/external/llmail_phase1_prepared_v1 \
  --models-dir models/llmail_short_baseline_v1 \
  --output-dir data/external/llmail_long_window_v1
```

Each runner writes a small result JSON even on a caught failure. After both, package only the two result files:

```bash
cd ~/cad_project
mkdir -p results/report_extension_v1
cp data/external/llmail_phase2_transfer_v2/phase2_transfer_result.json \
  results/report_extension_v1/
cp data/external/llmail_long_window_v1/long_email_result.json \
  results/report_extension_v1/
tar -czf ~/Desktop/cad-report-extension-v1.tar.gz \
  -C results report_extension_v1
```

Upload `cad-report-extension-v1.tar.gz`. If either command fails, preserve its result/error; do not change cutoffs/sample size to chase a preferred outcome. Runtime depends on CPU tokenization/indexing, GPU and local storage. Avoid starting another training job or backend concurrently.

## Reporting plan

Add actual observed results to a versioned report addendum, including failed attempts, sampling/exclusions, all aggregations and cutoff policies, class denominators and label provenance. Do not replace the weak original reserved results. Long-email coverage is an offline extension only; the native live gateway, its message-selection/session limits, and GPU cancellation remain separate engineering requirements. General protection, independent-source validation and production readiness must not be inferred from passing software checks or improved aggregation metrics.
