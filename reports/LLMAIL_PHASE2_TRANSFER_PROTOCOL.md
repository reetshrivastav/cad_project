# Bounded Phase 2 transfer check — frozen before execution

Update: the first run stopped before predictions on a suffix-format assumption (`level1a`). The failed result is preserved. Use the cached-payload retry in [long-email extension / repair protocol](LLMAIL_LONG_EMAIL_PROTOCOL.md); sampling, scenario task mapping, models and cutoffs remain unchanged.

This additional test fits within the remaining reporting window without new training or long-email engineering. It evaluates existing Phase 1 heads and both already frozen cutoffs on a deterministic bounded sample from the previously unused Phase 2 files. Phase 2 is the same publisher/challenge, not a separate-source benchmark or production incident corpus.

## Fixed protocol

- Download `labelled_unique_submissions_phase2.json` and `raw_submissions_phase2.jsonl` at source revision `1063bdf01ec8762b812d5e06ee768a06faa5a6f7`. Source payloads stay in ignored local storage.
- Exclude unclear/malformed labels and any normalized exact text or exact token-bag match against **all Phase 1 annotation texts**, including training, validation, reserved and previously excluded source cases. These are exact lexical checks, not a guarantee of near-duplicate/template independence.
- Join remaining texts to Phase 2 raw submissions with the publisher serialization. Record observed owners/levels; exclude unmatched or missing-team cases. An unseen-team claim requires all observed owners to be absent from the 224-team Phase 1 index. Text-new and text-plus-team-new results are reported separately. If no unseen-team sample exists, report that absence rather than substitute a claim of independence.
- Phase 2 levels 1/2 correspond to original retrieval scenarios 3/4, not original scenarios 1/2. Preserve the original Project Zenith and Q2 user queries. The script checks query identity and fails if the source does not fit this mapping; it does not silently invent a task.
- Sort eligible joined texts by SHA256 of `phase2-transfer-v1:` plus source text ID. Inspect only the first 5,000; score at most the first 2,000 whose full email and task each fit 256 tokens including special tokens. No truncation. Sampling does not use predicted scores, outcome quality or class balancing. Report source labels, overlap/length exclusions, sampling coverage and cohort size.
- Existing pair/task-only/content-only heads, checkpoint and both cutoff policies are unchanged. No fit, cutoff search, probability calibration or outcome-dependent resampling. Report empty/single-class cohorts explicitly; do not manufacture balanced accuracy or AUC where unsupported.

## Terminal 3; vLLM and gateway stopped

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/evaluate_llmail_phase2.py \
  --source-dir data/external/llmail_phase1_v1 \
  --group-dir data/external/llmail_phase1_groups_v2 \
  --models-dir models/llmail_short_baseline_v1 \
  --output-dir data/external/llmail_phase2_transfer_v1
```

Requires existing environment, internet for the two pinned data files, several GB of RAM/disk and the cached MiniLM checkpoint. CPU overlap preparation precedes a bounded GPU embedding/scoring run. No vLLM backend generation. Runtime depends on download speed/CPU; do not assume a fixed completion time. Failure evidence is preserved as `phase2_transfer_result.json`. If it fails, send the result/error instead of altering settings to obtain a preferred outcome.

Package the small result even if the check fails (do not package source payloads):

```bash
tar -czf ~/Desktop/llmail-phase2-transfer-v1.tar.gz \
  -C ~/cad_project/data/external/llmail_phase2_transfer_v1 \
  phase2_transfer_result.json
```

Upload `llmail-phase2-transfer-v1.tar.gz`. Results will be added to the final report as an explicitly scoped transfer addendum. No result is assumed in the current report edition. Long-email support remains deferred; existing gateway model/serving is unchanged.
