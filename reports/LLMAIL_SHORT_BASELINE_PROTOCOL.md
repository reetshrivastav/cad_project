# LLMail readiness result and short-email baseline preparation

The [uploaded readiness summary](evidence/llmail_readiness_20261023/llmail_readiness_summary.json) matches the tokenizer revision, preparation and screening source digests. Source-split row counts reconcile. This verifies operator-supplied aggregates, not an independent rerun over cloud payloads.

The first lexical screen is **incomplete**: it reached two million comparisons and skipped 215,753 overfull anchor queries. It nevertheless found 872 cross-split pairs at unigram Jaccard >=0.8 (268 train/validation, 562 train/test, 42 validation/test); 413 rows participated. Seventy-eight candidate pairs had identical normalized token bags. Neither a clean split nor semantic/template independence is established.

| Split | Original rows | Email exceeds 256 tokens | Fits email window before cleanup |
| --- | ---: | ---: | ---: |
| Train | 101,749 | 59,924 | 41,825 |
| Validation | 17,537 | 6,434 | 11,103 |
| Reserved test | 17,536 | 3,547 | 13,989 |

All tasks fit (maximum 13 tokens). Longest tokenized emails are 30,038 train, 20,221 validation and 12,912 test. Silent MiniLM truncation would discard substantial content and cannot support a full-email detection claim.

## Scoped next experiment

Prepare an initial **short-email source-annotation baseline**. Exclude any row whose task or full email exceeds 256 tokens including special tokens; do not truncate. Report exclusions by split and source label. This is selective coverage, not a solution to long emails. The original full-length exports and held-out split remain intact.

Among eligible short rows:

1. Index every Unicode-normalized, casefolded, whitespace-normalized full text and normalized token bag. Resolve all cross-split exact-key collisions by dropping the lower-priority row (`test > validation > train`). Exhaustively verify no normalized exact key survives in multiple splits.
2. Generate 64 deterministic MinHash values over word sets, grouped into 16 bands of four. Retrieve cross-split candidate pairs; verify unigram Jaccard >=0.8. Drop lower-priority matching rows. The word sets ignore order and semantics, so this is a conservative lexical policy.
3. If candidates exceed 500 per row or the two-million verification budget is reached, conservatively drop lower-priority endpoints for all remaining retrieved candidate pairs rather than skipping them. This may remove legitimate diversity; count these removals. No model outputs influence removal.

The MinHash search remains approximate; non-candidate similarities can be missed. No claim of exhaustive near-duplicate/template independence follows. The cleanup does not move rows across source-team splits or modify text. Full-length overlap findings are not assumed to apply only to short rows; the short subset is screened afresh. Model quality on longer inputs remains unmeasured.

## Terminal 3; terminals 1 and 2 stopped

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/prepare_llmail_short_baseline.py \
  --prepared-dir data/external/llmail_phase1_prepared_v1 \
  --output-dir data/external/llmail_short_baseline_v1
```

Uses existing NumPy and cached tokenizer, CPU only. No installations, downloads, GPU or fitting. Allow time and disk space for the SQLite index and local eligible/cleaned files; progress prints every 5,000 screened short rows. An untruncated-length tokenizer warning is expected for long inputs during eligibility checks.

```bash
cp ~/cad_project/data/external/llmail_short_baseline_v1/short_baseline_summary.json \
  ~/Desktop/llmail_short_baseline_summary.json
```

Upload only `llmail_short_baseline_summary.json`. Keep source payloads/indexes local. Once retained class counts are known, a fixed training/calibration protocol can use development rows only and reserve test scoring for a separate command. All labels remain publisher automated source annotations. The 203 benign emails and Phase 2 are still unused. Any eventual score must state short-email coverage and external-source/annotation limitations explicitly.
