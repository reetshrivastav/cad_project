"""
cache_pressure.py - Background vLLM KV-Cache Telemetry with Hysteresis & Trend Detection

Enhancements addressing reviewer feedback:
1. Exponential Moving Average (EMA) smoothing: Prevents knife-edge threshold oscillation.
2. Dual-threshold Hysteresis (Schmitt Trigger):
   - Enter HIGH-PRESSURE state when smoothed pressure >= 0.85
   - Exit HIGH-PRESSURE state only when smoothed pressure <= 0.70
3. Rate-of-Change (Trend) Detection: Identifies rapid memory fill rates (dp/dt > 0.10/s).
4. Safe Fallbacks: Uses conservative thresholds if telemetry is stale (> 5 seconds).
"""

import math
import os
import threading
import time
import requests

_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
_lock = threading.Lock()
_started = False

# Telemetry State
_raw_value = None
_smoothed_value = None
_last_sample_time = None
_previous_value = None
_pressure_rate = 0.0  # dp/dt (pressure change per second)
_high_pressure_active = False  # Hysteresis latch
_error = "No successful sample yet"

# Hysteresis & EMA Constants
HIGH_PRESSURE_ENTER = 0.85
HIGH_PRESSURE_EXIT = 0.70
RAPID_GROWTH_THRESHOLD = 0.10  # +10% per second indicates imminent saturation
EMA_ALPHA = 0.35  # Weight for current sample


class CachePressureMonitor:
    """Encapsulates hysteresis latching, EMA smoothing, and trend detection."""

    def __init__(
        self,
        high_threshold: float = HIGH_PRESSURE_ENTER,
        low_threshold: float = HIGH_PRESSURE_EXIT,
        rapid_growth_threshold: float = RAPID_GROWTH_THRESHOLD,
        ema_alpha: float = EMA_ALPHA,
    ):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.rapid_growth_threshold = rapid_growth_threshold
        self.ema_alpha = ema_alpha
        self.raw_value = None
        self.smoothed_value = None
        self.last_sample_time = None
        self.previous_value = None
        self.pressure_rate = 0.0
        self.high_pressure_active = False

    def record_occupancy(self, new_val: float, timestamp: float = None):
        if timestamp is None:
            timestamp = time.monotonic()
        self.previous_value = self.raw_value
        self.raw_value = new_val

        if self.last_sample_time is not None:
            dt = max(0.001, timestamp - self.last_sample_time)
            self.pressure_rate = (new_val - (self.previous_value if self.previous_value is not None else new_val)) / dt
        else:
            self.pressure_rate = 0.0

        self.last_sample_time = timestamp

        if self.smoothed_value is None:
            self.smoothed_value = new_val
        else:
            self.smoothed_value = self.ema_alpha * new_val + (1.0 - self.ema_alpha) * self.smoothed_value

        if not self.high_pressure_active:
            if self.smoothed_value >= self.high_threshold or self.pressure_rate >= self.rapid_growth_threshold:
                self.high_pressure_active = True
        else:
            if self.smoothed_value <= self.low_threshold and self.pressure_rate <= 0:
                self.high_pressure_active = False

        return {
            "policy": "protective" if self.high_pressure_active else "normal",
            "smoothed_pressure": self.smoothed_value,
            "rate_of_change_per_sec": self.pressure_rate,
            "high_pressure_latch": self.high_pressure_active,
        }


def parse_pressure(text):
    """Parses Prometheus metrics for vllm:kv_cache_usage_perc."""
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
            raise ValueError("Invalid KV-cache pressure value")
        values.append(value)
    if not values:
        raise ValueError("KV-cache pressure metric missing from Prometheus endpoint")
    return max(values)


def update_telemetry_state(new_val, timestamp):
    """Updates smoothed telemetry and evaluates hysteresis latch."""
    global _raw_value, _smoothed_value, _previous_value, _pressure_rate
    global _last_sample_time, _high_pressure_active, _error

    _previous_value = _raw_value
    _raw_value = new_val

    if _last_sample_time is not None:
        dt = max(0.01, timestamp - _last_sample_time)
        _pressure_rate = (new_val - (_previous_value or new_val)) / dt
    else:
        _pressure_rate = 0.0

    _last_sample_time = timestamp

    # Update Exponential Moving Average (EMA)
    if _smoothed_value is None:
        _smoothed_value = new_val
    else:
        _smoothed_value = EMA_ALPHA * new_val + (1.0 - EMA_ALPHA) * _smoothed_value

    # Evaluate Hysteresis Latch (Schmitt Trigger)
    if not _high_pressure_active:
        if _smoothed_value >= HIGH_PRESSURE_ENTER or _pressure_rate >= RAPID_GROWTH_THRESHOLD:
            _high_pressure_active = True
    else:
        if _smoothed_value <= HIGH_PRESSURE_EXIT and _pressure_rate <= 0:
            _high_pressure_active = False

    _error = None


def choose_thresholds(effective_state, sandbox=0.35, quarantine=0.75):
    """Computes thresholds accounting for hysteresis state and rapid trends."""
    if effective_state is None or effective_state.get("stale"):
        # Conservative fallback
        return max(0.20, round(sandbox - 0.10, 4)), max(0.60, round(quarantine - 0.10, 4))

    is_high = effective_state.get("high_pressure_latch", False)
    if is_high:
        return max(0.20, round(sandbox - 0.10, 4)), max(0.60, round(quarantine - 0.10, 4))

    return sandbox, quarantine


def _poll():
    global _error
    with requests.Session() as session:
        while True:
            try:
                response = session.get(f"{_URL}/metrics", timeout=(0.5, 0.5))
                response.raise_for_status()
                val = parse_pressure(response.text)
                now = time.monotonic()
                with _lock:
                    update_telemetry_state(val, now)
            except Exception as exc:
                with _lock:
                    _error = str(exc)
            time.sleep(1.0)


def snapshot():
    """Returns a thread-safe snapshot of smoothed pressure and hysteresis policy."""
    global _started
    with _lock:
        if not _started:
            threading.Thread(target=_poll, name="vllm-metrics-hysteresis", daemon=True).start()
            _started = True

        now = time.monotonic()
        age = None if _last_sample_time is None else now - _last_sample_time
        stale = age is None or age > 5.0

        effective_pressure = None if stale else _smoothed_value
        is_high = False if stale else _high_pressure_active

        state = {
            "metric": "vllm:kv_cache_usage_perc",
            "raw_pressure": _raw_value,
            "smoothed_pressure": round(_smoothed_value, 4) if _smoothed_value is not None else None,
            "pressure_rate_per_sec": round(_pressure_rate, 4),
            "high_pressure_latch": is_high,
            "sample_age_seconds": round(age, 2) if age is not None else None,
            "stale": stale,
            "last_error": _error,
            "policy": (
                "conservative_telemetry_unavailable" if stale
                else "high_pressure_active" if is_high
                else "normal"
            ),
        }

        sandbox_th, quarantine_th = choose_thresholds(state)
        state["sandbox_threshold"] = sandbox_th
        state["quarantine_threshold"] = quarantine_th
        return state


def current_thresholds(sandbox=0.35, quarantine=0.75):
    state = snapshot()
    return choose_thresholds(state, sandbox, quarantine)
