"""Small in-process rolling health tracker for selectable chat models."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    at: float
    success: bool
    ttft_ms: float | None
    duration_ms: float


_WINDOW_SECONDS = 30 * 60
_samples: dict[str, deque[Sample]] = defaultdict(lambda: deque(maxlen=500))


def record_model_result(
    model_id: str, *, success: bool, duration_ms: float, ttft_ms: float | None = None
) -> None:
    _samples[model_id].append(Sample(time.time(), success, ttft_ms, duration_ms))


def _recent(model_id: str) -> list[Sample]:
    now = time.time()
    items = _samples[model_id]
    while items and now - items[0].at > _WINDOW_SECONDS:
        items.popleft()
    return list(items)


def model_status(model_id: str, *, configured: bool) -> dict:
    empty_metrics = {
        "selectable": configured,
        "success_rate": None,
        "avg_latency_ms": None,
        "sample_count": 0,
        "congested": False,
    }
    if not configured:
        return {"status": "unavailable", "status_label": "暂不可用", **empty_metrics}
    samples = _recent(model_id)
    if not samples:
        return {"status": "available", "status_label": "可用", **empty_metrics}
    successes = [sample for sample in samples if sample.success]
    rate = len(successes) / len(samples)
    avg_latency = (
        sum(sample.duration_ms for sample in successes) / len(successes) if successes else None
    )
    metrics = {
        "selectable": True,
        "success_rate": round(rate, 4),
        "avg_latency_ms": round(avg_latency) if avg_latency is not None else None,
        "sample_count": len(samples),
        "congested": False,
    }
    consecutive_failures = 0
    for sample in reversed(samples):
        if sample.success:
            break
        consecutive_failures += 1
    # Runtime failures are advisory health signals, not proof that the model is
    # unusable. The router can still retry the requested model and fail over to
    # its configured chain, so keep it selectable and describe the temporary
    # degradation honestly. Only a missing provider configuration above is a
    # hard unavailable state.
    if consecutive_failures >= 3 or (len(samples) >= 5 and rate < 0.8):
        return {"status": "unstable", "status_label": "近期波动", **metrics}
    ttfts = sorted(sample.ttft_ms for sample in successes if sample.ttft_ms is not None)
    median_ttft = ttfts[len(ttfts) // 2] if ttfts else None
    metrics["congested"] = bool(median_ttft is not None and median_ttft > 6000)
    if rate < 0.97 or (median_ttft is not None and median_ttft > 6000):
        return {"status": "slow", "status_label": "稍慢", **metrics}
    return {"status": "smooth", "status_label": "流畅", **metrics}


def reset_health_for_tests() -> None:
    _samples.clear()
