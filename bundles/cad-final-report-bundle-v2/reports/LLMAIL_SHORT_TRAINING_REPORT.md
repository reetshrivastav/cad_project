# LLMail short-email baseline — verified native training results

The baseline fits training data but generalizes poorly at the fixed 0.5 cutoff to the source-negative validation cases. Keep it offline. Pair inputs have not shown an advantage over content-only on this experiment.

| Validation model | Source positives flagged / 1,852 | Source negatives incorrectly flagged / 40 | Balanced accuracy | ROC AUC |
| --- | ---: | ---: | ---: | ---: |
| Pair | 1,775 | 34 | 55.42% | 0.8909 |
| Task only | 1,838 | 40 | 49.62% | 0.7762 |
| Content only | 1,779 | 33 | 56.78% | 0.8907 |
| Always source-positive | 1,852 | 40 | 50.00% | 0.5000 |

Pair training balanced accuracy was 99.58%, compared with validation 55.42%; pair validation raw accuracy was 94.13%. The always-positive validation raw accuracy is 97.89%. High ROC AUC/average precision do not establish an acceptable fixed-cutoff false-alarm rate, particularly with only 40 source-negative validation rows and substantial filtering/cluster bias. Changing the threshold is possible future development work but has not been done or validated here.

The experiment uses automated publisher source labels on selectively retained short emails and one-email task projections. Source negatives are not independently adjudicated ordinary benign messages. Aggressive conservative filtering and long-input exclusions remain material limitations. These validation results are not downstream attack success or independent real-world security accuracy.

## Integrity and scope

Exact uploaded [archive](evidence/llmail_short_training_20261023/llmail-short-training-v1.tar.gz) contains three UBJ heads, metadata and training report. The [verified summary](evidence/llmail_short_training_20261023/verified_summary.json) reconciles training/module/feature digests, preparation file references, model hashes, development IDs/class counts and recomputed metrics from all recorded probabilities. CUDA inference itself was not reproduced in the cloud. Lab source commit `ea19eedc0203891a824948211e076f8f817714ef`, MiniLM CUDA/FP16 checkpoint `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; 3,896 training and 1,892 validation inputs, zero recorded test inputs encoded. No serving model changed.

## Next diagnostic: publisher benign-email collection

Before changing labels or retraining, measure whether the frozen models also flag the separately supplied 203 publisher benign emails. This distinguishes ordinary-email false alarms from disagreement with competition source-negative annotation targets. It does not establish which cause explains any result; low false alarms would not validate the negative labels, and high false alarms would not by itself identify a specific training cause.

Fixed model files and 0.5 cutoff. Use scenario 1's legitimate summary query, never the attacker objective. Select only full emails that fit 256 tokens, exclude empty/duplicate entries and normalized exact development overlaps, and report all exclusions. No reserved Phase 1 test file is opened or scored. Same-source collection, no independent human review, incomplete semantic-overlap guarantees and single-email projection remain explicit. Once inspected, the benign collection is diagnostic data and cannot later be presented as a fresh untouched test after tuning.

Terminal 3, with vLLM and gateway stopped:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/evaluate_llmail_benign.py \
  --source-dir data/external/llmail_phase1_v1 \
  --data-dir data/external/llmail_short_baseline_v1 \
  --models-dir models/llmail_short_baseline_v1 \
  --output results/llmail_benign_diagnostic_v1.json
```

```bash
cp ~/cad_project/results/llmail_benign_diagnostic_v1.json \
  ~/Desktop/llmail_benign_diagnostic_v1.json
```

Upload `llmail_benign_diagnostic_v1.json`. This uses the already installed environment and pinned CUDA/FP16 MiniLM; no training, downloads of datasets or model replacement. Review negative-data policy and candidate changes using development evidence before deciding when to spend the reserved Phase 1 test. Long-email handling, cross-source evaluation and downstream agent validation remain separate work.
