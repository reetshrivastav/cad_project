# Script and test inventory

Generated from repository files for evidence edition 2.0. Descriptions are module docstrings; consult each CLI with `--help`. Training/evaluation jobs must follow their protocols and fresh-output rules.

## Scripts

| Script | Purpose |
|---|---|
| [analyze_benign_evaluation.py](../scripts/analyze_benign_evaluation.py) | Verify and summarize recorded candidate scoring offline; never loads models. |
| [analyze_bipia_evaluation.py](../scripts/analyze_bipia_evaluation.py) | Verify recorded BIPIA-derived tier classifications offline, without models. |
| [analyze_context_v2.py](../scripts/analyze_context_v2.py) | Reconcile archived lab v2 evidence without loading model weights or running CUDA. |
| [analyze_context_v2_transfer.py](../scripts/analyze_context_v2_transfer.py) | Verify recorded frozen-model wording-transfer evidence without GPU inference. |
| [analyze_gpu_burst.py](../scripts/analyze_gpu_burst.py) | Analyze recorded multi-request GPU trials offline; no server requests. |
| [analyze_gpu_pilot.py](../scripts/analyze_gpu_pilot.py) | Derive tables/plots from a recorded pilot; never contacts servers. |
| [analyze_gpu_replications.py](../scripts/analyze_gpu_replications.py) | Offline analysis of all nine prespecified GPU replication runs. |
| [analyze_injection_candidate.py](../scripts/analyze_injection_candidate.py) | Verify candidate-only diagnostic evidence and preserve clean-control failure. |
| [analyze_llmail_benign.py](../scripts/analyze_llmail_benign.py) | Reconcile recorded benign diagnostic probabilities; no inference. |
| [analyze_llmail_human_review.py](../scripts/analyze_llmail_human_review.py) | Record reviewer-supplied targeted adjudication with explicit input-integrity exclusions. |
| [analyze_llmail_phase2.py](../scripts/analyze_llmail_phase2.py) | Reconcile frozen content-only Phase 2 predictions without loading an encoder. |
| [analyze_llmail_reserved.py](../scripts/analyze_llmail_reserved.py) | Reconcile reserved test archive and frozen cutoff metrics; no inference. |
| [analyze_llmail_review_comparison.py](../scripts/analyze_llmail_review_comparison.py) | Reconcile AI/source review comparison and rescore saved validation probabilities. |
| [analyze_llmail_training.py](../scripts/analyze_llmail_training.py) | Reconcile archived LLMail training outputs without loading model weights. |
| [analyze_policy_calibration.py](../scripts/analyze_policy_calibration.py) | Validate and summarize a saved policy calibration without loading model weights. |
| [analyze_report_extension.py](../scripts/analyze_report_extension.py) | Verify recorded report-extension results, including full window coverage. |
| [analyze_wrapper_diagnostic.py](../scripts/analyze_wrapper_diagnostic.py) | Verify paired wrapper outcomes offline without loading model weights. |
| [audit_external_datasets.py](../scripts/audit_external_datasets.py) | Metadata-only public dataset audit. Standard library; no payload/model downloads. |
| [audit_llmail_groups.py](../scripts/audit_llmail_groups.py) | Exact Phase 1 annotation/raw join and team-component audit; no model fitting. |
| [benchmark_embedding_paths.py](../scripts/benchmark_embedding_paths.py) | Compare MiniLM inference paths offline; does not change the gateway or models. |
| [benchmark_gpu_pilot.py](../scripts/benchmark_gpu_pilot.py) | Bounded direct-vLLM vs gateway pilot; run on the lab, not a full DoS test. |
| [build_final_report_figures.py](../scripts/build_final_report_figures.py) | Build final report figures from retained measurements; no lab execution. |
| [calibrate_policy_candidates.py](../scripts/calibrate_policy_candidates.py) | Offline mechanism-test calibration; never forwards requests to an LLM. |
| [check_embedding_routing_parity.py](../scripts/check_embedding_routing_parity.py) | Offline native feature/risk/tier parity check; never forwards to vLLM. |
| [check_live_gateway.py](../scripts/check_live_gateway.py) | Bounded sequential live check; requires running gateway and vLLM. |
| [check_llmail_readiness.py](../scripts/check_llmail_readiness.py) | CPU token-length and bounded lexical-leakage screen; no fitting or scoring. |
| [check_sandbox_live.py](../scripts/check_sandbox_live.py) | One idle-backend sandbox cap check using a previously calibrated candidate. |
| [compare_llmail_label_review.py](../scripts/compare_llmail_label_review.py) | Compare completed blinded development review with source labels; never fit a model. |
| [download_llmail_phase1.py](../scripts/download_llmail_phase1.py) | Download pinned LLMail Phase 1 and summarize schemas; no fitting or GPU use. |
| [evaluate_benign_candidates.py](../scripts/evaluate_benign_candidates.py) | Score the frozen reviewed candidate pool using native live CUDA/FP16 features. |
| [evaluate_bipia_candidates.py](../scripts/evaluate_bipia_candidates.py) | Offline native scoring of a frozen BIPIA-derived controlled memo corpus. |
| [evaluate_context_v2.py](../scripts/evaluate_context_v2.py) | Score the frozen synthetic topic-test split after separate v2 training. |
| [evaluate_context_v2_transfer.py](../scripts/evaluate_context_v2_transfer.py) | Frozen-model wording-transfer diagnostic; synthetic labels, no deployment claims. |
| [evaluate_injection_candidate.py](../scripts/evaluate_injection_candidate.py) | Shadow-only specialized detector diagnostic; does not import/start the gateway. |
| [evaluate_llmail_benign.py](../scripts/evaluate_llmail_benign.py) | Frozen-head false-alarm diagnostic on publisher benign emails, short inputs only. |
| [evaluate_llmail_long.py](../scripts/evaluate_llmail_long.py) | Frozen-model full-coverage sliding-window test on bounded reserved long emails. |
| [evaluate_llmail_phase2.py](../scripts/evaluate_llmail_phase2.py) | Bounded frozen-head Phase 2 transfer test; exact Phase 1 overlap exclusions. |
| [evaluate_llmail_reserved.py](../scripts/evaluate_llmail_reserved.py) | One reserved short-email test, frozen heads and original/validation-selected cutoffs. |
| [evaluate_wrapper_diagnostic.py](../scripts/evaluate_wrapper_diagnostic.py) | Paired guard/tag diagnostic using the already-cached pinned candidate. |
| [export_llmail_label_review.py](../scripts/export_llmail_label_review.py) | Export blinded development-only source-label review; no fitting/test inputs. |
| [final_project_check.py](../scripts/final_project_check.py) | Record final local CPU regression and frozen-artifact verification; no services required. |
| [pinned_injection_runtime.py](../scripts/pinned_injection_runtime.py) | Pinned detector loading for follow-up diagnostics, not gateway integration. |
| [prepare_bipia_candidates.py](../scripts/prepare_bipia_candidates.py) | Freeze a BIPIA-derived controlled-context classification test without scoring. |
| [prepare_context_v2.py](../scripts/prepare_context_v2.py) | Prepare synthetic grouped task/content contrast cases without model scores. |
| [prepare_heldout_candidates.py](../scripts/prepare_heldout_candidates.py) | Audit native training exposure and freeze unscored, unlabeled review candidates. |
| [prepare_llmail_phase1.py](../scripts/prepare_llmail_phase1.py) | Export source-labeled task/email projections under a frozen component split. |
| [prepare_llmail_short_baseline.py](../scripts/prepare_llmail_short_baseline.py) | No-truncation short-email subset with conservative cross-split lexical cleanup. |
| [prepare_wrapper_diagnostic.py](../scripts/prepare_wrapper_diagnostic.py) | Freeze a 2x2 guard-wording/tag diagnostic; development cases, never scored here. |
| [profile_ingress.py](../scripts/profile_ingress.py) | Profile the real gateway extractor on the lab host; never calls vLLM. |
| [run_report_extension.py](../scripts/run_report_extension.py) | Run cached Phase 2 retry and bounded long-email evaluation sequentially; package results. |
| [train_context_v2.py](../scripts/train_context_v2.py) | Train separately versioned task/content prototype; never scores test rows. |
| [train_llmail_short_baseline.py](../scripts/train_llmail_short_baseline.py) | Train offline short-email source-label models; never tokenizes or scores test inputs. |
| [verify_native_artifacts.py](../scripts/verify_native_artifacts.py) | Verify the retained native archive or a lab directory without unpickling. |

## Test modules

Run `.venv/bin/python -m unittest discover -s tests -v` with servers stopped. These tests include CPU behavior and evidence reconciliation; they do not execute new physical-GPU benchmarks.

- [test_benign_evaluation.py](../tests/test_benign_evaluation.py)
- [test_benign_evidence.py](../tests/test_benign_evidence.py)
- [test_bipia_candidates.py](../tests/test_bipia_candidates.py)
- [test_bipia_evidence.py](../tests/test_bipia_evidence.py)
- [test_burst_analysis.py](../tests/test_burst_analysis.py)
- [test_calibration_evidence.py](../tests/test_calibration_evidence.py)
- [test_candidate_evidence.py](../tests/test_candidate_evidence.py)
- [test_context_v2.py](../tests/test_context_v2.py)
- [test_context_v2_evidence.py](../tests/test_context_v2_evidence.py)
- [test_context_v2_transfer_evidence.py](../tests/test_context_v2_transfer_evidence.py)
- [test_embedding_runtime.py](../tests/test_embedding_runtime.py)
- [test_external_dataset_audit.py](../tests/test_external_dataset_audit.py)
- [test_gpu_gateway.py](../tests/test_gpu_gateway.py)
- [test_gpu_pilot.py](../tests/test_gpu_pilot.py)
- [test_gpu_replications.py](../tests/test_gpu_replications.py)
- [test_heldout_preparation.py](../tests/test_heldout_preparation.py)
- [test_injection_candidate.py](../tests/test_injection_candidate.py)
- [test_lab_training.py](../tests/test_lab_training.py)
- [test_live_check.py](../tests/test_live_check.py)
- [test_llmail_benign.py](../tests/test_llmail_benign.py)
- [test_llmail_groups.py](../tests/test_llmail_groups.py)
- [test_llmail_human_review.py](../tests/test_llmail_human_review.py)
- [test_llmail_intake.py](../tests/test_llmail_intake.py)
- [test_llmail_long.py](../tests/test_llmail_long.py)
- [test_llmail_phase2.py](../tests/test_llmail_phase2.py)
- [test_llmail_preparation.py](../tests/test_llmail_preparation.py)
- [test_llmail_readiness.py](../tests/test_llmail_readiness.py)
- [test_llmail_reserved_evidence.py](../tests/test_llmail_reserved_evidence.py)
- [test_llmail_review_diagnostic.py](../tests/test_llmail_review_diagnostic.py)
- [test_llmail_review_import.py](../tests/test_llmail_review_import.py)
- [test_llmail_short_baseline.py](../tests/test_llmail_short_baseline.py)
- [test_llmail_short_model.py](../tests/test_llmail_short_model.py)
- [test_llmail_thresholds.py](../tests/test_llmail_thresholds.py)
- [test_native_artifacts.py](../tests/test_native_artifacts.py)
- [test_phase2_content_evidence.py](../tests/test_phase2_content_evidence.py)
- [test_pilot_analysis.py](../tests/test_pilot_analysis.py)
- [test_policy_calibration.py](../tests/test_policy_calibration.py)
- [test_report_extension.py](../tests/test_report_extension.py)
- [test_wrapper_diagnostic.py](../tests/test_wrapper_diagnostic.py)
- [test_wrapper_evidence.py](../tests/test_wrapper_evidence.py)
