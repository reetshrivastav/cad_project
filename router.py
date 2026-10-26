"""
router.py - Decoupled Multi-Threat Decision Engine & Resource Policy

Enhancements addressing reviewer feedback:
1. Decoupled Risk Mitigation:
   - Separates R_inject (Adversarial Jailbreak/Injection Risk) from R_exhaust (Resource Exhaustion Risk).
2. Graceful Resource Degradation:
   - Legitimate high-demand requests (High R_exhaust, Low R_inject) are NOT rejected with HTTP 403!
     Instead, they receive a "clamped_quota" policy where output tokens are clamped to a safe
     server ceiling (e.g. 512 or 1024 tokens) and allowed to complete.
3. True Security Quarantine:
   - HTTP 403 is reserved strictly for high R_inject threats.
4. Backward Compatibility:
   - Maintains assign_tier(risk) for existing scalar callers while offering assign_decoupled_tier().
"""

import numpy as np
import pandas as pd

SANDBOX_THRESHOLD = 0.35
REJECT_THRESHOLD = 0.75

# Resource Policy Constants
SANDBOX_MAX_OUTPUT_TOKENS = 256
CLAMPED_QUOTA_MAX_TOKENS = 512
DEFAULT_MAX_OUTPUT_TOKENS = 2048
SANDBOX_MAX_COMPUTE_SECONDS = 5.0

# Cost Model Constants (illustrative estimates)
COST_PER_1K_PROMPT_TOKENS = 0.0015
COST_PER_1K_OUTPUT_TOKENS = 0.006
CACHE_HIT_PREFILL_DISCOUNT = 0.85


def assign_tier(risk: pd.Series, thresholds=None) -> pd.Series:
    """Legacy/scalar tier assignment based on composite risk score."""
    sandbox, quarantine = thresholds or (SANDBOX_THRESHOLD, REJECT_THRESHOLD)
    tier = pd.Series("full", index=risk.index)
    tier[risk >= sandbox] = "sandbox"
    tier[risk >= quarantine] = "quarantine"
    return tier


def assign_decoupled_tier(
    r_inject: pd.Series,
    r_exhaust: pd.Series,
    thresholds=None,
) -> pd.DataFrame:
    """Decoupled decision matrix mapping orthogonal risk vectors to targeted mitigations.
    
    Mitigation Matrix:
    - High R_inject (>= quarantine)                     -> 'quarantine' (HTTP 403)
    - Medium R_inject (>= sandbox)                      -> 'sandbox' (Tools stripped, prompt spotlighted)
    - Low R_inject + High R_exhaust (>= clamp_thresh)  -> 'clamped_quota' (Allowed, token budget clamped to 512)
    - Low R_inject + Low R_exhaust                      -> 'full' (Normal unconstrained execution)
    """
    sandbox_th, quarantine_th = thresholds or (SANDBOX_THRESHOLD, REJECT_THRESHOLD)
    exhaust_clamp_th = sandbox_th

    df_out = pd.DataFrame(index=r_inject.index)
    tier = pd.Series("full", index=r_inject.index)
    action = pd.Series("allow_unconstrained", index=r_inject.index)
    token_cap = pd.Series(DEFAULT_MAX_OUTPUT_TOKENS, index=r_inject.index)

    # 1. Evaluate Resource Exhaustion (Graceful Clamping)
    high_exhaust = r_exhaust >= exhaust_clamp_th
    tier[high_exhaust] = "clamped_quota"
    action[high_exhaust] = "clamp_output_tokens"
    token_cap[high_exhaust] = CLAMPED_QUOTA_MAX_TOKENS

    # 2. Evaluate Security Injection (Overrides Resource Decisions)
    med_inject = r_inject >= sandbox_th
    tier[med_inject] = "sandbox"
    action[med_inject] = "sandbox_isolate_tools_and_prompt"
    token_cap[med_inject] = SANDBOX_MAX_OUTPUT_TOKENS

    high_inject = r_inject >= quarantine_th
    tier[high_inject] = "quarantine"
    action[high_inject] = "http_403_reject"
    token_cap[high_inject] = 0

    df_out["tier"] = tier
    df_out["action"] = action
    df_out["token_cap"] = token_cap
    df_out["r_inject"] = r_inject
    df_out["r_exhaust"] = r_exhaust
    return df_out


def estimate_cost_dollars(
    df: pd.DataFrame, tier: pd.Series, cache_hit_prob: np.ndarray
) -> pd.Series:
    """Estimates dollar cost incurred under assigned tier policies."""
    prompt_cost = (df["prompt_length_tokens"] / 1000.0) * COST_PER_1K_PROMPT_TOKENS
    prompt_cost = prompt_cost * (1 - CACHE_HIT_PREFILL_DISCOUNT * cache_hit_prob)

    effective_output_tokens = df["predicted_output_tokens"].clip(upper=None).astype(float)

    # Apply tier-specific caps
    sandboxed = tier.eq("sandbox")
    clamped = tier.eq("clamped_quota")
    effective_output_tokens = effective_output_tokens.where(
        ~sandboxed, np.minimum(effective_output_tokens, SANDBOX_MAX_OUTPUT_TOKENS)
    )
    effective_output_tokens = effective_output_tokens.where(
        ~clamped, np.minimum(effective_output_tokens, CLAMPED_QUOTA_MAX_TOKENS)
    )

    output_cost = (effective_output_tokens / 1000.0) * COST_PER_1K_OUTPUT_TOKENS
    total = prompt_cost + output_cost

    # Quarantined requests incur 0 execution cost
    total = total.where(~tier.eq("quarantine"), 0.0)
    return total
