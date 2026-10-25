# LLMail preparation verified; token and lexical checks

The uploaded [preparation summary](evidence/llmail_preparation_20261023/llmail_preparation_summary.json) matches the frozen split-plan and export-script hashes. Exported class totals, annotation reasons and exclusions reconcile: 136,822 definite-label texts exported; 23,911 unclear, two malformed and six unmatched definite labels excluded. Cloud verification preserves operator-reported file hashes; source payloads remain local. No training or model scores have been produced.

Max email lengths are 32,696/32,188/32,703 characters in train/validation/test. These cannot safely be represented by silent truncation to MiniLM's 256-token window. Next count untruncated token lengths and screen lexical overlaps before deciding the explicit windowing and exclusion policy.

## Terminal 3; servers stopped

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/check_llmail_readiness.py \
  --prepared-dir data/external/llmail_phase1_prepared_v1 \
  --output-dir data/external/llmail_phase1_readiness_v1
```

This uses the existing gateway environment's Transformers tokenizer, not CUDA. The pinned MiniLM tokenizer must already be in the local cache; the script does not download dependencies or model weights. It verifies preparation artifact hashes first. Allow additional disk space for a local lexical index and time for CPU tokenization and SQLite screening of 136,822 texts. No new installation or sudo required. A tokenizer warning about sequence length is possible: truncation is explicitly disabled for these length measurements.

```bash
cp ~/cad_project/data/external/llmail_phase1_readiness_v1/readiness_summary.json \
  ~/Desktop/llmail_readiness_summary.json
```

Upload `llmail_readiness_summary.json` only. Keep the SQLite file and payloads local. If the command fails, paste its error rather than restarting servers or installing another model.

## Interpretation boundaries

The lexical screen uses Unicode-normalized lowercase word sets, eight lowest stable token hashes, cross-split candidate retrieval and exact unigram Jaccard verification at 0.8. It ignores token order, word frequency and semantics, so matches are candidates for conservative leakage control, not proof that attacks are identical. Empty-token texts receive no anchors and are not compared. Each anchor query is capped at 200 candidates, and total pair comparisons at two million; skipped buckets and exhausted budget are explicitly reported. Consequently zero detected pairs cannot prove absence of duplicates or template overlap. A separate complete normalized exact check or a more thorough near-duplicate pass may be required if screening is insufficient; do not characterize this bounded heuristic as exhaustive.

The screen reports aggregate reserved-test similarities and token lengths, not labels/predictions for threshold tuning, and does not print raw text. This is dataset QA, not a model evaluation. Do not alter the original source payloads or frozen split files. Findings will inform a separately versioned cleaned development preparation; any removal policy and long-input policy must be fixed before training and reserved scoring. Positive/negative targets still represent source automated annotations, not independently adjudicated malicious intent.
