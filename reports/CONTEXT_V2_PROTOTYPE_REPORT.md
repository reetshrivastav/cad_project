# Task/content v2 prototype — native lab evidence

The paired representation classified 59/60 synthetic topic-test cases correctly (98.33%), compared with 48/60 for task-only and 36/60 for content-only. This supports the task/content representation on this development exercise. It does not establish general prompt-injection protection, downstream attack prevention or production readiness.

## Recorded experiment

The lab trained three separately saved XGBoost models with MiniLM CUDA/FP16 embeddings, Python 3.10.12 and XGBoost 3.2.0. The encoder checkpoint was `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Source commit: `2adf9e2d3e842e0a4d51147dcf73919510b347d5`.

The frozen corpus contains 400 AI/programmatically labeled cases: 280 training, 60 validation and 60 test, separated into 28/6/6 topic groups. Templates are shared across splits. Training records report zero test inputs encoded; model fitting uses training rows only. Review probability cutoff remains 0.5. No threshold or hyperparameter selection was performed using these test results.

| Model | Training correct | Validation correct | Test correct | Test redirections reviewed | Allowed cases incorrectly reviewed |
| --- | --- | --- | --- | --- | --- |
| Pair | 280/280 | 60/60 | 59/60 | 24/24 | 1/36 |
| Task only | 224/280 | 48/60 | 48/60 | 24/24 | 12/36 |
| Content only | 168/280 | 36/60 | 36/60 | 8/24 | 8/36 |

Training accuracy is resubstitution. Test observations are clustered in six topics and share authoring templates, so 60 rows are not 60 independently sourced security scenarios. Single-input baselines encounter identical inputs with conflicting task-dependent labels by construction. Their lower scores demonstrate the information limitation of those representations on this corpus, not superiority over production detectors.

The pair model's sole test error is `CTX-032-01`: summarizing a clean community cinema seating memo. Review probability was 0.73998493. No redirection case was missed, but this ordinary-task false alarm must remain in the record.

## Evidence verification

The exact uploaded archive, including three UBJ model files, is retained under [context_v2_scoring_20261023](evidence/context_v2_scoring_20261023). The [verified summary](evidence/context_v2_scoring_20261023/verified_summary.json) contains archive/member SHA256 checksums and the full error case. The analyzer checks frozen corpus identity, input rows, split IDs, model artifact hashes, feature/training/scoring source hashes, embedding revision and runtime consistency, all training/validation/test confusion counts and per-topic metrics. This reconciles operator-supplied evidence; cloud verification does not reproduce CUDA inference or independently attest the recorded execution.

Models remain inside the evidence archive to avoid conflicts with the lab's untracked `models/context_native_v2` directory. No serving model or gateway routing was changed.

```bash
.venv/bin/python scripts/analyze_context_v2.py \
  reports/evidence/context_v2_scoring_20261023/context-v2-lab-results.tar.gz \
  --output results/context_v2_verified_summary.json
```

## Follow-up: wording transfer (now completed)

Keep the three models, encoder checkpoint and cutoff frozen. The prepared 48-case challenge uses eight new topics and different task, memo and redirection wording. It includes 16 redirection cases and 32 allowed cases, including analysis and quotation of the same instruction-bearing content. The runner never fits a model. Its labels are still AI-authored workflow proxies; this is a post-test diagnostic, not independently adjudicated security evidence. It was authored after seeing the original test result.

Leave terminal 1 (vLLM) and terminal 2 (gateway) stopped. Run in terminal 3:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python -m unittest discover -s tests -v &&
.venv/bin/python scripts/evaluate_context_v2_transfer.py \
  --models-dir models/context_native_v2 \
  --output results/context_v2_wording_transfer.json
cp results/context_v2_wording_transfer.json ~/Desktop/
```

**Completed outcome:** pair reviewed only 4/16 redirections and falsely reviewed 1/32 allowed cases. See [transfer report](CONTEXT_V2_WORDING_TRANSFER_REPORT.md). The commands above document the completed run; do not rerun unchanged scoring.

Original execution instructions: Upload `context_v2_wording_transfer.json`. Do not retrain or overwrite the existing models. If transfer fails, retain the failure and treat these cases as development data before any subsequent revision. Even success requires a further independently sourced, reviewed task/content evaluation before deployment. Real downstream attack-success measurement, trusted-context provenance, conversation handling and resource-pressure/cancellation work remain separate.
