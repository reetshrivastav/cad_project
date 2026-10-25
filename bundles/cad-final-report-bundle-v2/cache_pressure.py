"""Background vLLM KV-cache pressure monitoring."""
import math
import os
import threading
import time

import requests

_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
_lock = threading.Lock()
_started = False
_value = None
_updated = None
_error = "No successful sample yet"


def parse_pressure(text):
    values = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0].startswith("#"):
            continue
        name = fields[0].split("{", 1)[0]
        if name != "vllm:kv_cache_usage_perc":
            continue
        value = float(fields[1])
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid KV-cache pressure")
        values.append(value)
    if not values:
        raise ValueError("KV-cache pressure metric missing")
    return max(values)


def choose_thresholds(pressure, sandbox=0.35, quarantine=0.75):
    # Unknown/stale telemetry uses conservative thresholds.
    if pressure is None or pressure > 0.85:
        return max(0.20, round(sandbox - 0.10, 10)), max(0.60, round(quarantine - 0.10, 10))
    return sandbox, quarantine


def _poll():
    global _value, _updated, _error
    with requests.Session() as session:
        while True:
            try:
                response = session.get(
                    f"{_URL}/metrics", timeout=(0.5, 0.5)
                )
                response.raise_for_status()
                value = parse_pressure(response.text)
                with _lock:
                    _value = value
                    _updated = time.monotonic()
                    _error = None
            except Exception as exc:
                with _lock:
                    _error = str(exc)
            time.sleep(1)


def snapshot():
    global _started
    with _lock:
        if not _started:
            threading.Thread(
                target=_poll, name="vllm-metrics", daemon=True
            ).start()
            _started = True
        age = None if _updated is None else time.monotonic() - _updated
        stale = age is None or age > 5
        effective = None if stale else _value
        sandbox, quarantine = choose_thresholds(effective)
        return {
            "metric": "vllm:kv_cache_usage_perc",
            "pressure": _value,
            "sample_age_seconds": age,
            "stale": stale,
            "last_error": _error,
            "policy": (
                "conservative_telemetry_unavailable" if stale
                else "high_pressure" if effective > 0.85
                else "normal"
            ),
            "sandbox_threshold": sandbox,
            "quarantine_threshold": quarantine,
        }


def current_thresholds(sandbox=0.35, quarantine=0.75):
    state = snapshot()
    pressure = None if state["stale"] else state["pressure"]
    return choose_thresholds(pressure, sandbox, quarantine)
