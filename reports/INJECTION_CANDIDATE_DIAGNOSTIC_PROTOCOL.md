# Specialized injection detector: shadow diagnostic

Prepared 23 October 2026. Native candidate inference is pending; this does not claim the injection weakness has been fixed. The next concrete experiment evaluates a dedicated pretrained binary detector on the already-inspected cases, without changing the serving gateway or the frozen native baseline.

## Why a separate candidate

Native v1 has demonstrated constrained GPU admission protection but also benign overblocking and low tier coverage on the controlled BIPIA-derived corpus. Tightened thresholds left all 72 full-tier constructed attack variants unchanged. This motivates testing a specialized content detector before committing to retraining/integration; it does not prove the new model understands trust boundaries or will improve results.

The selected candidate is `protectai/deberta-v3-base-prompt-injection-v2` at pinned revision `89b085cd330414d3e7d9dd787870f315957e1e9f`. This ID/revision is listed as the default v2 model in ProtectAI's published [LLM Guard scanner](https://github.com/protectai/llm-guard/blob/main/llm_guard/input_scanners/prompt_injection.py). The observed scanner source uses `injection_score > 0.92`; that is the primary diagnostic rule. A separately reported `>0.50` operating point is prespecified, not selected after seeing outcomes. These probabilities and thresholds are not the native XGBoost risk scale or its graduated routing tiers. This runner compares full-precision probabilities; the referenced LLM Guard scanner rounds to three decimals before its comparison, so exact near-threshold outcomes and the overall scanner implementation are not claimed identical.

The source URL, observed source hash, model pin and thresholds are recorded in [candidate_manifest.json](evidence/injection_candidate_preparation_20261023/candidate_manifest.json). The published scanner reference uses a mutable branch; the observed hash records what was read, while the model revision itself is immutable. No scanner source code is imported or copied into the application. The cloud's destination policy denied Hugging Face access, so weights/tokenizer/model card and actual CUDA inference have not been verified here. This is not a missing-credential diagnosis; do not request a token merely from that cloud denial. Initial model access must be tested on the lab with its existing network/cache.

## Frozen diagnostics, not fresh held-out data

The script validates the existing evidence and uses exactly:

- 200 AI-labeled benign prompts, preserving annotation limitations.
- 75 BIPIA-derived constructed attack contexts, retaining source-derived intent and wrapper limitations.
- One clean BIPIA memo control, reported separately.

These 276 cases have already been inspected. Candidate upstream training overlap is unknown, including possible exposure to public source material. This is a diagnostic/regression comparison, not independent human-labeled evaluation, official BIPIA ASR or fresh held-out generalization. If it informs model selection or thresholds, preserve a new untouched evaluation set for later claims.

Every input is the exact existing complete prompt; this diagnostic does not use oracle extraction of the known attack span. The script never fetches embedded links or follows prompt instructions. It uses the explicit model config's SAFE/INJECTION label mapping rather than assuming a class index. Missing or ambiguous mappings fail. Inputs longer than the verified tokenizer/model limit (at most 512 tokens) are retained as errors; no silent truncation or partial-input safety claim is allowed.

## Lab execution, Terminal 3 only

Stop vLLM and the gateway in Terminals 1 and 2. The candidate needs GPU memory and internet for the first model download. Use the existing `.venv`; no vLLM-environment/package changes are requested. Download duration depends on network/cache. The script uses standard Transformers, disables remote model code, requires safetensors weights and requires CUDA/FP16. It loads the candidate only, not MiniLM or the native classifier.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
.venv/bin/python -m unittest discover -s tests -v &&
.venv/bin/python scripts/evaluate_injection_candidate.py \
  --output results/injection_candidate_shadow_v1.json
```

If model access, safetensors availability, tokenizer compatibility or initialization fails, retain the error and diagnose it before changing packages or trying another model. Do not change to an unpinned revision, silently assume class labels, disable verification or fall back to untrusted model code. No repeated request for credentials is warranted without inspecting the actual access error.

The script saves a full result before exiting nonzero for per-row scoring errors. Keep that evidence; do not count errors as safe outcomes or rerun over it. Existing outputs are protected. When the pinned artifacts are already cached, `--local-files-only` supports a separately named reproducibility run without downloads.

After a completed result:

```bash
cp ~/cad_project/results/injection_candidate_shadow_v1.json \
  ~/Desktop/injection_candidate_shadow_v1.json
```

Upload the JSON for verification. It includes all rows, both threshold comparisons, baseline decisions, resolved labels/config, weight and model-card hashes, model-card snapshot, runtime/device/dtype, per-row timing and PyTorch peak allocation. The model card should be reviewed for declared training data, licensing and intended use before integration or redistribution of weights; no model weights are committed by this diagnostic.

## Analysis and integration gate

Report offered/scored/error counts and flagged fractions separately for each group and threshold. Preserve category outcomes and the clean-control result. Compare candidate flags with native quarantine and any restriction only as **different policy outcomes**, not equivalent safety guarantees. No gateway HTTP block, sandbox generation cap, trust-boundary enforcement or downstream attack prevention is tested.

Evaluate both missed attacks and new benign flags; do not choose whichever threshold looks best and call it independently validated. A detector that flags legitimate quoted text or the clean wrapper may be unsuitable even if its attack count rises. If coverage remains weak or benign flags are unacceptable, retain that negative outcome and revise the approach. No integration occurs automatically on a good count: new context/role handling, long-input behavior and a separate untouched validation set remain necessary.

Timing includes tokenization, transfer, cold inference and synchronization. It is not a warmed ingress benchmark or a promise to meet the original latency goal. PyTorch peak allocation is not total device VRAM, energy or monetary cost. Serving-layer integration must separately quantify added latency and resource cost.

The frozen model and all existing reports remain unchanged. The experiment is a candidate comparison; it does not by itself make the gateway trust-aware or cure the recorded limitations.

Cloud verification: all 64 CPU regression tests passed, including integrity of the 276 diagnostic cases, config-driven label indexing, strict threshold boundaries and error/empty-denominator handling. Actual pinned tokenizer/weights/card and GPU inference remain unverified until the lab run.
