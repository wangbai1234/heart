"""
SS07 Orchestration — CircuitBreaker per docs/design/orchestrator_min_viable.md §3.3.

Three-state machine: closed → open → half_open → closed.
Process-singleton BreakerRegistry with pre-registered services.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Pre-registered service defaults ────────────────────────────────

_DEFAULTS: Dict[str, dict] = {
    "safety": {"threshold": 5, "window_sec": 60, "open_sec": 30},
    "composer": {"threshold": 3, "window_sec": 60, "open_sec": 30},
    "llm": {"threshold": 5, "window_sec": 60, "open_sec": 30},
}


# ── CircuitBreaker ──────────────────────────────────────────────────


@dataclass
class CircuitBreaker:
    """Per-service circuit breaker with three-state transition logic.

    States:
        closed   — normal operation, failures accumulate
        open     — no calls allowed, auto-transitions to half_open after open_sec
        half_open — allows one probe call; success → closed, failure → open
    """

    name: str
    threshold: int = 5
    window_sec: int = 60
    open_sec: int = 30

    # Internal state
    _failure_count: int = field(default=0, init=False, repr=False)
    _state: str = field(default="closed", init=False, repr=False)
    _open_since: Optional[float] = field(default=None, init=False, repr=False)
    _window_start: Optional[float] = field(default=None, init=False, repr=False)

    def record_success(self) -> None:
        """Record a successful call.

        If in half_open state, reset to closed. Otherwise no-op.
        """
        if self._state == "half_open":
            self._state = "closed"
            self._failure_count = 0
            self._window_start = None
            self._open_since = None
            logger.info("breaker_reset_to_closed", breaker_name=self.name)

    def record_failure(self) -> None:
        """Record a failed call.

        Increments the sliding-window failure counter. When threshold
        is reached within the window, transitions to open.
        """
        now = time.monotonic()

        # Reset window if expired
        if self._window_start is None or (now - self._window_start) > self.window_sec:
            self._window_start = now
            self._failure_count = 0

        self._failure_count += 1

        if self._failure_count >= self.threshold:
            if self._state != "open":
                self._state = "open"
                self._open_since = now
                logger.warning(
                    "breaker_opened",
                    breaker_name=self.name,
                    failure_count=self._failure_count,
                    threshold=self.threshold,
                )

    def is_open(self) -> bool:
        """Check if the circuit is currently open.

        Side effect: if the open duration has elapsed, auto-transitions
        to half_open and returns False.
        """
        if self._state == "open":
            if (
                self._open_since is not None
                and (time.monotonic() - self._open_since) >= self.open_sec
            ):
                self._state = "half_open"
                self._failure_count = 0
                self._window_start = None
                logger.info(
                    "breaker_half_open",
                    breaker_name=self.name,
                    open_duration_sec=round(time.monotonic() - self._open_since, 1),
                )
                return False
            return True
        return False

    @property
    def state(self) -> str:
        """Current breaker state (for observability)."""
        return self._state


# ── BreakerRegistry ─────────────────────────────────────────────────


class BreakerRegistry:
    """Process-singleton registry for per-service circuit breakers.

    Usage:
        registry = BreakerRegistry()
        breaker = registry.get("safety")
        if breaker.is_open():
            ...
    """

    _instance: Optional["BreakerRegistry"] = None
    _breakers: Dict[str, CircuitBreaker]

    def __new__(cls) -> "BreakerRegistry":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._breakers = {}
            instance._init_defaults()
            cls._instance = instance
        return cls._instance

    def _init_defaults(self) -> None:
        for name, cfg in _DEFAULTS.items():
            self._breakers[name] = CircuitBreaker(name=name, **cfg)

    def get(self, name: str) -> CircuitBreaker:
        """Get or lazily create a circuit breaker by service name."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name)
        return self._breakers[name]

    def get_all(self) -> Dict[str, CircuitBreaker]:
        """Return all registered breakers (for diagnostics)."""
        return dict(self._breakers)
