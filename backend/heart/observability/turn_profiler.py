"""
Turn Profiler — per-turn latency and cost breakdown.

Records phase timings into:
  - OpenTelemetry spans (per-phase)
  - Prometheus histograms (heart_turn_phase_duration_ms)
  - Structured "turn_profile" log line on span close

Enabled via env HEART_TURN_PROFILER=1. When disabled (< 5ms overhead):
  - TurnProfiler.current() returns a no-op sentinel
  - All span() context managers are bare yields
  - No Prometheus / OTel work is done

Usage:
    with TurnProfiler(session_id=str(session_id)) as p:
        with p.span("auth"):
            verify_jwt(token)
        with p.span("model_router"):
            p.annotate(model_name="deepseek-reasoner")
            response = await llm.call(...)
            p.annotate(input_tokens=500, output_tokens=200, cost_usd=0.002)
"""

from __future__ import annotations

import contextvars
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger(__name__)

# ── Prometheus metrics ────────────────────────────────────────────

TURN_PHASE_DURATION_MS = Histogram(
    "heart_turn_phase_duration_ms",
    "Turn phase wall-clock duration in milliseconds",
    ["phase"],
    buckets=[0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000],
)

TURN_MODEL_COST_USD = Histogram(
    "heart_turn_model_cost_usd",
    "Per-turn LLM cost in USD",
    ["model"],
    buckets=[0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0],
)

TURN_MODEL_TOKENS = Histogram(
    "heart_turn_model_tokens",
    "Per-turn LLM token usage",
    ["model", "direction"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 20000, 40000, 80000],
)

LLM_COST_DOLLARS_TOTAL = Counter(
    "heart_llm_cost_dollars_total",
    "Cumulative LLM cost in USD",
    ["provider", "model"],
)

LLM_TOKENS_TOTAL = Counter(
    "heart_llm_tokens_total",
    "Cumulative LLM token usage",
    ["model", "token_type"],
)

# ── Context-var thread / asyncio safe ─────────────────────────────

_profiler_var: contextvars.ContextVar[Optional["TurnProfiler"]] = contextvars.ContextVar(
    "heart_turn_profiler", default=None
)

_collected_profiles: List[Dict[str, Any]] = []

_ENABLED: Optional[bool] = None


def get_collected_profiles() -> List[Dict[str, Any]]:
    """Return all collected turn profile dicts (for programmatic access)."""
    return list(_collected_profiles)


def reset_collected_profiles() -> None:
    """Clear collected profiles (primarily for testing)."""
    _collected_profiles.clear()


def _is_enabled() -> bool:
    global _ENABLED
    if _ENABLED is None:
        val = os.environ.get("HEART_TURN_PROFILER", "0").strip()
        if val == "1":
            _ENABLED = True
        else:
            try:
                from heart.core.config import settings

                _ENABLED = settings.heart_turn_profiler.strip() == "1"
            except Exception:
                _ENABLED = False
    return _ENABLED


# ── Data structures ───────────────────────────────────────────────


@dataclass
class PhaseRecord:
    phase: str
    elapsed_ms: float
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnProfile:
    session_id: str
    started_at: float
    finished_at: float = 0.0
    phases: List[PhaseRecord] = field(default_factory=list)


# ── OTel tracer (lazy) ────────────────────────────────────────────


def _get_tracer():
    try:
        from opentelemetry import trace

        return trace.get_tracer("heart.turn_profiler")
    except Exception:
        return None


# ── TurnProfiler ──────────────────────────────────────────────────


class TurnProfiler:
    """Per-turn latency and cost profiler.

    Context manager that records phase timings.  Accessible throughout
    the call-stack via TurnProfiler.current() (contextvar-backed).

    When HEART_TURN_PROFILER != 1 the constructor returns a lightweight
    no-op sentinel whose .span() yields instantly and whose .annotate()
    is a no-op.
    """

    @staticmethod
    def current() -> "TurnProfiler":
        """Return the currently-active profiler or a no-op sentinel."""
        p = _profiler_var.get(None)
        if p is not None:
            return p
        return _NOOP  # type: ignore[return-value]

    def __new__(cls, session_id: str = ""):
        if not _is_enabled():
            return _NOOP  # type: ignore[return-value]
        return super().__new__(cls)

    def __init__(self, session_id: str = ""):
        if not _is_enabled():
            return
        self.enabled = True
        self._session_id = session_id
        self._started_at = time.monotonic()
        self._phases: List[PhaseRecord] = []
        self._tracer = _get_tracer()
        self._entered = False

    # ── Context manager ────────────────────────────────────────

    def __enter__(self) -> "TurnProfiler":
        if not _is_enabled():
            return self
        _profiler_var.set(self)
        self._entered = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not _is_enabled():
            return
        _profiler_var.set(None)
        self._entered = False
        self._emit()

    # ── Public API ─────────────────────────────────────────────

    @contextmanager
    def span(self, phase: str) -> Generator[None, None, None]:
        """Context manager that times a named phase.

        Usage:
            with p.span("retriever"):
                memories = await service.retrieve(...)
        """
        t0 = time.monotonic()
        otel_span = None
        if self._tracer is not None:
            otel_span = self._tracer.start_span(phase)
        rec = PhaseRecord(phase=phase, elapsed_ms=0.0)
        self._phases.append(rec)
        try:
            yield
        finally:
            rec.elapsed_ms = (time.monotonic() - t0) * 1000.0
            TURN_PHASE_DURATION_MS.labels(phase=phase).observe(rec.elapsed_ms)
            if otel_span is not None:
                otel_span.set_attribute("elapsed_ms", rec.elapsed_ms)
                otel_span.end()

    def annotate(self, **kwargs: Any) -> None:
        """Add key-value annotations to the current (last-opened) phase.

        Called inside a span() block, e.g.:
            with p.span("model_router"):
                response = await llm.call(...)
                p.annotate(
                    model_name="deepseek-reasoner",
                    input_tokens=512,
                    output_tokens=128,
                    cost_usd=0.002,
                )
        """
        if self._phases:
            self._phases[-1].annotations.update(kwargs)

    def current_span_name(self) -> Optional[str]:
        """Return the name of the currently-open span (if any)."""
        if self._phases:
            return self._phases[-1].phase
        return None

    # ── Internal ───────────────────────────────────────────────

    def _emit(self) -> None:
        """Emit the full turn_profile structured log line + Prometheus."""
        total_elapsed = (time.monotonic() - self._started_at) * 1000.0
        total_cost = 0.0

        hot_path_phases = {
            "auth",
            "safety_pre",
            "retriever",
            "composer",
            "model_router",
            "anti_pattern",
        }
        cold_path_phases = {"memory_encode", "inner_loop"}

        breakdown: Dict[str, float] = {}
        for rec in self._phases:
            breakdown[rec.phase] = rec.elapsed_ms
            model_name = rec.annotations.get("model_name", "unknown")
            provider = rec.annotations.get("provider", model_name)
            if "cost_usd" in rec.annotations:
                cost = float(rec.annotations["cost_usd"])
                total_cost += cost
                TURN_MODEL_COST_USD.labels(model=model_name).observe(cost)
                LLM_COST_DOLLARS_TOTAL.labels(provider=provider, model=model_name).inc(cost)
            if "input_tokens" in rec.annotations:
                itok = float(rec.annotations["input_tokens"])
                TURN_MODEL_TOKENS.labels(model=model_name, direction="input").observe(itok)
                LLM_TOKENS_TOTAL.labels(model=model_name, token_type="input").inc(itok)
            if "output_tokens" in rec.annotations:
                otok = float(rec.annotations["output_tokens"])
                TURN_MODEL_TOKENS.labels(model=model_name, direction="output").observe(otok)
                LLM_TOKENS_TOTAL.labels(model=model_name, token_type="output").inc(otok)

        hot_ms = sum(v for k, v in breakdown.items() if k in hot_path_phases)
        cold_ms = sum(v for k, v in breakdown.items() if k in cold_path_phases)

        profile_dict = {
            "session_id": self._session_id,
            "total_elapsed_ms": round(total_elapsed, 2),
            "hot_path_ms": round(hot_ms, 2),
            "cold_path_ms": round(cold_ms, 2),
            "total_cost_usd": round(total_cost, 6),
            "phases": [
                {
                    "phase": r.phase,
                    "elapsed_ms": round(r.elapsed_ms, 2),
                    **r.annotations,
                }
                for r in self._phases
            ],
        }

        logger.info(
            "turn_profile",
            **profile_dict,
        )

        # Store for programmatic access (profile_demo)
        _collected_profiles.append(profile_dict)


# ── No-op sentinel ────────────────────────────────────────────────


class _NoOpProfiler:
    enabled = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @contextmanager
    def span(self, phase: str) -> Generator[None, None, None]:
        yield

    def annotate(self, **kwargs: Any) -> None:
        pass

    def current_span_name(self) -> Optional[str]:
        return None


_NOOP = _NoOpProfiler()
