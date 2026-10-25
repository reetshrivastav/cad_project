> Update, 25 October 2026: the cached content-only Phase 2 check is complete. See the [final report](FINAL_PROJECT_REPORT.md#phase-2-content-only-transfer). Commands below are historical reproduction instructions, not pending required work.

# Long-email result and Phase 2 scope correction — 24 October 2026

The long-email extension completed in the lab. **All 300 sampled emails were covered by 723 token windows, representing 130,735 unique content-token positions.** There were 276 source-positive and 24 source-negative email targets. The unchanged models remain unsuitable for general deployment: max pooling increases positive recall but also flags most source negatives.

The exact [extension archive](evidence/report_extension_20261024/cad-report-extension-v1.tar.gz) and [verified summary](evidence/report_extension_20261024/verified_summary.json) preserve both the successful long run and another failed Phase 2 schema preflight. For long inputs, verification checks frozen hashes, row alignment, source-class totals, interval coverage, each aggregation and all cutoff metrics from recorded probabilities. Actual token identities and GPU embeddings are not independently reproduced. One inherited raw metric scope string incorrectly says short emails; it comes from the unchanged metric helper, not the experiment's actual input scope. The raw archive is retained unchanged and derived reporting explicitly describes long-email windows.

## Coverage and method

The original full reserved set contains 3,547 long emails (3,283 source positives, 264 negatives). A fixed hash selected 300, not a score-dependent or class-balanced sample. Every selected email was evaluated in full: content-token windows of capacity 254, overlap 32, plus tokenizer special tokens. There were no whole-email budget exclusions. The source commit was `417762c`; runner timing reports approximately 26.8 seconds for the long job, including local work. This is batch experiment wall time, not per-request ingress latency or backend generation time.

The original short-trained heads and both cutoffs remain fixed. First-window, max-window and mean-window comparisons were prespecified. Source labels are email-level; no chunk labels or malicious-span locations are supplied. The maximum-window result is not proof of locating an attack in the tail.

## Pair-head results

| Aggregation | Cutoff | Source positives flagged / 276 | Source negatives flagged / 24 | Balanced accuracy |
| --- | --- | ---: | ---: | ---: |
| First | 0.5 | 187 (67.75%) | 20 (83.33%) | 42.21% |
| Max | 0.5 | 274 (99.28%) | 22 (91.67%) | 53.80% |
| Mean | 0.5 | 269 (97.46%) | 22 (91.67%) | 52.90% |
| First | Frozen short-validation | 105 (38.04%) | 17 (70.83%) | 33.61% |
| Max | Frozen short-validation | 218 (78.99%) | 18 (75.00%) | 51.99% |
| Mean | Frozen short-validation | 55 (19.93%) | 7 (29.17%) | 45.38% |

An always-positive rule already achieves 92% raw accuracy because 276/300 targets are positive. Pair max at 0.5 also achieves 92% raw accuracy while flagging 22/24 negatives. Thus high recall/raw accuracy does not establish useful discrimination. Only 24 source negatives inform these estimates; they are not human-verified production false positives.

Content-only max at 0.5 flags 271/276 positives and 22/24 negatives (balanced accuracy 53.26%). At the existing higher cutoff it flags 218/276 positives and 18/24 negatives (51.99%). Task-only is effectively unchanged by aggregation and is near 50% balanced accuracy. The verified JSON retains all three heads, three aggregations and both cutoffs. No winner is selected for serving.

Compared with first-window scores at 0.5, max scores flag 87 additional source-positive pair cases and two additional source negatives. That is a change in email-level agreement, not independently proven malicious-span recovery. Mean scoring at higher cutoffs illustrates dilution. Long-input coverage is technically achieved offline, while long-email detection quality remains unresolved. Native live gateway behavior is unchanged.

## Phase 2: preserve failure, remove unverified task assumptions

The cached retry stopped before predictions at `Unknown Phase 2 level: level3c`. The raw identifiers do not support the earlier two-level assumption. Rather than broaden another guessed trusted-task mapping, the next evaluation is explicitly **content-only**. That existing head never uses the trusted task feature and can be scored on source text/annotations without assigning an unverified scenario query.

The code records every observed level ID without interpreting it, retains the same pinned files, Phase 1 normalized-text/token-bag exclusions, owner novelty cohort, hash sample (inspect at most 5,000, score at most 2,000 short texts), content-head weights and both numerical cutoffs. No Phase 2 predictions were available when this narrower scope was selected. Pair/task heads are intentionally not evaluated until trusted-context provenance is resolved. No new download or long rerun is required.

Terminal 3, servers stopped:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/evaluate_llmail_phase2.py \
  --source-dir data/external/llmail_phase1_v1 \
  --group-dir data/external/llmail_phase1_groups_v2 \
  --models-dir models/llmail_short_baseline_v1 \
  --phase2-source-dir data/external/llmail_phase2_transfer_v1 \
  --content-only \
  --output-dir data/external/llmail_phase2_content_v1
```

```bash
tar -czf ~/Desktop/llmail-phase2-content-v1.tar.gz \
  -C ~/cad_project/data/external/llmail_phase2_content_v1 \
  phase2_transfer_result.json
```

Upload `llmail-phase2-content-v1.tar.gz`, including if it fails. Long-email evidence will be included in report edition 1.1 now; actual Phase 2 predictions will be appended only after supplied and verified. Do not rerun the existing long experiment, alter a cutoff based on these long results, or treat same-publisher transfer as independent-source security validation.
