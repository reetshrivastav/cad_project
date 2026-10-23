# First LLMail short-email training run

The [uploaded cleanup summary](evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json) reconciles with preparation and cleanup source hashes. Eligible, removed and retained class counts reconcile. No normalized exact text/token-bag key survives across splits according to the local exhaustive check; approximate MinHash screening does not prove semantic/template independence. Cloud verification does not reproduce the local payload cleanup.

| Split | Source True | Source False | Total retained |
| --- | ---: | ---: | ---: |
| Training | 3,648 | 248 | 3,896 |
| Validation | 1,852 | 40 | 1,892 |
| Reserved test (not scored) | 13,282 | 707 | 13,989 |

The cleanup removed 47,140 of 66,917 short rows (70.45%), including 37,929 training and 9,211 validation rows. There were 623 verified cross-split Jaccard pairs, but over 22 million candidate edges were handled conservatively without verifying Jaccard because their candidate sets exceeded the per-row cap. Thus the removals are **not 47,140 confirmed duplicates**. This aggressive, test-prioritized selection changes the development distribution and can bias results. It supplies a limited exploratory baseline, not a definitive cleaned real-world benchmark. Long rows remain entirely outside this experiment.

An always-source-positive rule already scores 97.89% validation accuracy, with zero source-negative specificity and 50% balanced accuracy. Do not interpret high raw accuracy alone as detector quality. Only 40 validation source negatives remain; estimates are unstable, clustered by source authoring and not human-adjudicated.

## Fixed training protocol

- MiniLM checkpoint `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CUDA/FP16 normalized embeddings. Task and full email each must fit 256 tokens including special tokens; no truncation. No encoder fine-tuning.
- Separate pair, task-only and content-only XGBoost heads. Pair recipe is unchanged from the v2 prototype. No IDs, labels, annotation reasons or component identifiers are encoder input features.
- 150 trees, maximum depth 4, learning rate 0.05, row/column sampling 0.9, seed 42, CPU tree fitting with two threads. Class-balanced sample weights `n/(2*n_class)` computed from training labels only.
- Fixed positive cutoff 0.5. No early stopping, hyperparameter search, calibration or cutoff selection in this run. Report training resubstitution and validation separately, including source-positive recall, source-negative specificity, balanced accuracy, ROC AUC and average precision. Include an always-positive baseline.
- Read/encode training and validation rows only; reserved test artifact is hashed but never parsed, tokenized, encoded or scored. Reserved scoring will use a separate later command after the run is reviewed.
- Source True/False are publisher automated annotation targets, not guaranteed malicious/benign ground truth. No deployment or downstream attack-success claim.

## Terminal 3 — actual GPU embeddings, offline training

Keep vLLM and gateway stopped to leave GPU memory available. Use the existing gateway `.venv`; no additional installations or sudo.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python -m unittest discover -s tests -v &&
.venv/bin/python scripts/train_llmail_short_baseline.py \
  --data-dir data/external/llmail_short_baseline_v1 \
  --output-dir models/llmail_short_baseline_v1
```

Package only the newly saved heads, metadata and training report (not the source dataset or MiniLM weights):

```bash
cd ~/cad_project
tar -czf ~/Desktop/llmail-short-training-v1.tar.gz \
  models/llmail_short_baseline_v1
```

Upload `llmail-short-training-v1.tar.gz`. Do not overwrite v1/v2 gateway artifacts. Existing serving is unchanged; this module is not imported by the gateway. If training fails, paste the error before rerunning into a partially populated model directory.

## What this does not finish

Independent reviewed evaluation, other-source transfer, long-email modeling and agent-level attack-success prevention remain unmeasured. The test set is reserved from model fitting but has participated in documented dataset QA and test-priority cleanup; it is not a completely untouched independently sourced corpus. A stronger follow-up should revisit the aggressive filtering strategy rather than treating narrow success as sufficient for production.
