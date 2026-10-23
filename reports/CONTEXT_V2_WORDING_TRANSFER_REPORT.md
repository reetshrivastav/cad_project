# Frozen context v2 wording transfer — 23 October 2026

The pair model reviewed only 4/16 redirection cases under new wording, missing 12. It also falsely reviewed one of 32 allowed cases. The earlier 59/60 topic-test result does not establish wording robustness. Keep v2 offline.

| Frozen model | Correct / 48 | Redirections reviewed / 16 | Missed redirections | False reviews / 32 allowed |
| --- | --- | --- | --- | --- |
| Pair | 35 (72.92%) | 4 (25%) | 12 | 1 (3.13%) |
| Task only | 32 (66.67%) | 0 | 16 | 0 |
| Content only | 32 (66.67%) | 0 | 16 | 0 |

An always-allow rule would also score 32/48, illustrating why accuracy alone hides missed redirections. The paired representation remains somewhat better on this diagnostic, but its 25% redirection coverage is inadequate evidence for deployment. These are workflow-proxy classifications, not measured successful attacks against an LLM.

## Scope and integrity

The 48 cases span eight new topics, with new task, memo and redirection wording. There are 16 redirection and 32 allowed cases, including analysis/quotation of the same instruction-bearing content. Labels and text are AI-authored. Cases were constructed after inspecting the first topic test, so this is a development diagnostic, not independent security validation. Multiple input factors changed together; this experiment cannot isolate whether task wording, content wording or topic caused the failures.

The exact uploaded [result](evidence/context_v2_transfer_scoring_20261023/context_v2_wording_transfer.json) records CUDA/FP16 inference at source commit `e31deddefbc36cd9b6671c69f61c9d54f6176c33`. Its metadata, three model hashes and encoder revision match the previous topic test. Cutoff remained 0.5. The [verified summary](evidence/context_v2_transfer_scoring_20261023/verified_summary.json) reconciles all 48 input rows per model, recorded probabilities, decisions and confusion counts and retains all 13 pair-model errors. Cloud verification did not reproduce GPU inference.

One clean weekday extraction (`TRANSFER-01-02`, harbour buoy inspection) was falsely reviewed with probability 0.66070813. Several missed redirections have probabilities near 0.02–0.10; these are not all borderline 0.5 decisions. Lowering the cutoff on these inspected cases would constitute tuning and would require a fresh test set.

## Next work

1. Freeze this negative result and existing v2 artifacts. Do not rerun unchanged scoring or deploy this model.
2. Prepare a broader task/content corpus with multiple independently written task and redirection families, ordinary requests, and analysis/quotation controls. Establish trusted-task provenance in the intended application; a client-supplied field alone does not establish trust.
3. Split by authoring/template family as well as topic before fitting. Obtain independent human review of the reserved test labels. Previously inspected cases, including this transfer set, may be development/regression cases only.
4. Train a separately versioned candidate with the same single-input baselines; choose any cutoff on development data. Evaluate once on reserved families before considering shadow integration.

Do not substitute another narrow synthetic success for independent evidence. Live gateway resource protection remains supported by its separate controlled GPU experiments; this diagnostic changes the injection-model assessment, not those measurements. Downstream attack-success measurement, conversation handling and backend cancellation remain separate work.

To reproduce evidence reconciliation (no vLLM or gateway needed):

```bash
.venv/bin/python scripts/analyze_context_v2_transfer.py \
  reports/evidence/context_v2_transfer_scoring_20261023/context_v2_wording_transfer.json \
  --output results/context_v2_transfer_verified.json
```
