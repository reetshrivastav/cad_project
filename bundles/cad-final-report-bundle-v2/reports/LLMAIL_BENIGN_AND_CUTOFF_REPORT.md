# LLMail benign diagnostic and frozen cutoff experiment

The publisher's 203-email benign collection yielded 160 eligible unique emails, with 43 duplicate occurrences excluded. No long-input or normalized exact development-overlap exclusions were recorded. The [uploaded result](evidence/llmail_benign_20261023/llmail_benign_diagnostic_v1.json) and [verified summary](evidence/llmail_benign_20261023/verified_summary.json) reconcile source/model/scorer hashes, ID coverage, decisions and metrics. Source filtering and CUDA inference were not independently reproduced by cloud verification.

| Frozen head, cutoff 0.5 | Flagged / 160 | Publisher-benign flag rate |
| --- | ---: | ---: |
| Pair | 20 | 12.5% |
| Task only | 160 | 100% |
| Content only | 8 | 5% |

These same-source, publisher-designated benign examples are not independently human-reviewed production ground truth. They use one scenario query and one-email projections; approximate development overlap has not been ruled out. The collection is now diagnostic evidence, not fresh test data after subsequent tuning. Pair inputs have not shown a consistent benefit over content-only. The poor source-negative validation behavior cannot simply be dismissed as annotation noise given the observed ordinary-email flags; this diagnostic alone does not identify the causal training problem.

## Validation-only operating-cutoff experiment

Before another fit, freeze a transparent operating-point rule and assess whether score ranking is useful at a higher cutoff. The rule was designed after inspecting validation/benign diagnostics; the numerical cutoff is computed using **validation source-negative probabilities only**, not benign probabilities, positive scores or reserved-test data:

Choose the smallest representable float64 cutoff at least 0.5 that flags at most `floor(0.10 * N_negative)` validation source negatives. With 40 negatives, allow at most four flags. Handle ties by placing the cutoff strictly above the corresponding negative probability using `nextafter`; apply future comparisons in float64. This is operating-cutoff selection, not probability calibration, nor an approved production false-positive target.

| Head | Frozen adjusted cutoff | Validation positive recall | Validation negative specificity |
| --- | ---: | ---: | ---: |
| Pair | 0.9539673328399659 | 79.86% | 90% |
| Task only | 0.7515993714332582 | 0.22% | 100% |
| Content only | 0.9574561119079591 | 76.73% | 90% |

All three adjusted cutoffs flag zero of the already inspected 160 benign emails. This is reused diagnostic evidence, not independent confirmation. Only 40 validation negatives inform cutoff selection; clustered sampling and filtering make uncertainty substantial. The task-only head loses almost all recall and remains a comparison baseline, not a useful candidate. Freeze **all three** cutoffs before reserved scoring and report all outcomes without selecting a winner from the test.

The exact [policy](evidence/llmail_benign_20261023/threshold_policy.json) binds model metadata and selector-module hashes. Heads are unchanged; no retraining has occurred. Both original and adjusted cutoff results will be reported on the same reserved rows, preserving the original negative findings.

## Next terminal-3 command: reserved short-email test

Keep vLLM and gateway stopped; this uses CUDA/FP16 MiniLM embeddings, not backend generation. No extra packages, model fitting or threshold selection. Only the existing 13,989 reserved short-email rows are scored once (13,282 source positives, 707 source negatives). These were reserved from fitting and numerical cutoff selection, but were already involved in dataset QA and priority cleanup; they are not independent-source, untouched-in-every-respect evidence.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python scripts/evaluate_llmail_reserved.py \
  --data-dir data/external/llmail_short_baseline_v1 \
  --models-dir models/llmail_short_baseline_v1 \
  --output results/llmail_reserved_short_v1.json
```

Package only the output:

```bash
cd ~/cad_project
tar -czf ~/Desktop/llmail-reserved-short-v1.tar.gz \
  -C results llmail_reserved_short_v1.json
```

Upload `llmail-reserved-short-v1.tar.gz`. Do not tune on the result and then call these same cases a fresh held-out evaluation. Longer emails, separate-source transfer, independently reviewed labels and downstream agent prevention remain unmeasured. Existing serving stays unchanged even if this limited experiment succeeds.
