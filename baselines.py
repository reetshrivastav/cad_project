"""
baselines.py - Standard Systems & Security Baselines for LLM Serving Comparison

Implements standard production baselines addressing reviewer feedback:
1. ServerSideTokenClamp: Non-ML baseline enforcing a fixed server-side output token clamp.
2. TokenBucketLimiter: Standard cloud per-tenant token-bucket rate limiter.
3. StaticKeywordFilter: Classical keyword/regex pattern filter.
4. DecoupledGatewayBaseline: Our adaptive gateway with decoupled scoring and real sandboxing.
"""

import time
import re
from typing import Dict, Any, Tuple, Optional


class ServerSideTokenClamp:
    """Baseline 1: Static server-side output token cap.
    
    Protects against infinite token demands by capping requested completion tokens
    to a server-wide ceiling (e.g., 512 or 1024 tokens) with 0 ms overhead.
    Does NOT detect semantic prompt injection.
    """

    def __init__(self, max_allowed_tokens: int = 512):
        self.max_allowed_tokens = max_allowed_tokens

    def process_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        clamped_payload = dict(payload)
        req_tokens = payload.get("max_tokens")
        if req_tokens is None or int(req_tokens) > self.max_allowed_tokens:
            clamped_payload["max_tokens"] = self.max_allowed_tokens

        meta = {
            "baseline": "server_side_token_clamp",
            "original_max_tokens": req_tokens,
            "effective_max_tokens": clamped_payload["max_tokens"],
            "action": "clamped" if req_tokens and int(req_tokens) > self.max_allowed_tokens else "passed",
        }
        return clamped_payload, meta


class TokenBucketLimiter:
    """Baseline 2: Per-tenant token-bucket rate limiter.
    
    Standard cloud API defense: tracks per-session token burn over sliding time windows.
    Rejects requests when a tenant exhausts their allocated tokens-per-minute quota.
    """

    def __init__(self, capacity_tokens: int = 10000, refill_rate_per_sec: float = 100.0):
        self.capacity = float(capacity_tokens)
        self.refill_rate = refill_rate_per_sec
        self.buckets: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}

    def _refill(self, tenant_id: str, now: float):
        if tenant_id not in self.buckets:
            self.buckets[tenant_id] = self.capacity
            self.last_update[tenant_id] = now
            return

        dt = now - self.last_update[tenant_id]
        refill = dt * self.refill_rate
        self.buckets[tenant_id] = min(self.capacity, self.buckets[tenant_id] + refill)
        self.last_update[tenant_id] = now

    def check_admit(
        self, tenant_id: str, requested_tokens: int
    ) -> Tuple[bool, Dict[str, Any]]:
        now = time.monotonic()
        self._refill(tenant_id, now)

        cost = float(requested_tokens or 512)
        admitted = self.buckets[tenant_id] >= cost

        if admitted:
            self.buckets[tenant_id] -= cost

        meta = {
            "baseline": "token_bucket_limiter",
            "tenant_id": tenant_id,
            "remaining_budget": round(self.buckets[tenant_id], 1),
            "admitted": admitted,
        }
        return admitted, meta


class StaticKeywordFilter:
    """Baseline 3: Classical rule-based keyword/regex filter.
    
    Scans prompts for known attack signatures and demand scale triggers.
    Fast (< 1 ms) but brittle to natural paraphrasing and synonym replacement.
    """

    def __init__(self):
        self.jailbreak_patterns = [
            r"(?i)\bjailbreak\b",
            r"(?i)\bDAN\s+mode\b",
            r"(?i)ignore\s+(all\s+)?previous\s+instructions",
            r"(?i)developer\s+mode\b",
            r"(?i)system\s+override\b",
        ]
        self.sponge_patterns = [
            r"(?i)100[,\s]?000\s+words",
            r"(?i)write\s+a\s+novel",
            r"(?i)never\s+stop",
            r"(?i)repeat\s+forever",
        ]

    def evaluate(self, prompt: str) -> Tuple[str, Optional[str]]:
        for pat in self.jailbreak_patterns:
            if re.search(pat, prompt):
                return "quarantine", f"matched_jailbreak_pattern: {pat}"

        for pat in self.sponge_patterns:
            if re.search(pat, prompt):
                return "quarantine", f"matched_sponge_pattern: {pat}"

        return "full", None
