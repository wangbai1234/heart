"""
Circuit Breaker — per-service failure protection per SS07 §3.8 + §4.3.

States: CLOSED → (failures > threshold) → OPEN → (time elapsed) → HALF_OPEN.

Design invariants (from runtime_specs/07_agent_orchestration.md):
  INV-O-7: Circuit Breaker 触发后, 该 subsystem 切换 fallback 模式 (cached or default)
  O-7:     每个 sub-agent 必须有 timeout + circuit breaker
  O-10:    任何 subsystem 失败必须有降级策略

Usage::

    from heart.infra.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

    cb = CircuitBreaker("main_llm", CircuitBreakerConfig(
        failure_threshold=5, window_seconds=60, open_duration_seconds=30,
    ))

    try:
        result = await call_llm()
        cb.record_success()
    except Exception:
        cb.record_failure()
        result = fallback_response()

Author: 心屿团队
"""

from __future__ import annotations

import structlog
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = structlog.get_logger()


# ============================================================
# Enums
# ============================================================


class CircuitState(str, Enum):
    """Three-state breaker model per §4.3."""
    CLOSED = "closed"       # Normal — calls pass through
    OPEN = "open"           # Blocked — calls rejected immediately
    HALF_OPEN = "half_open" # Testing — single probe call allowed


# ============================================================
# Configuration
# ============================================================


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker.

    Per spec §3.8:
      - ss01_anchor:      threshold=5,  window=60s, open_duration=30s
      - ss02_memory:      threshold=10, window=60s, open_duration=60s
      - main_llm:         threshold=5,  window=60s, open_duration=30s
    """
    failure_threshold: int = 5
    window_seconds: float = 60.0
    open_duration_seconds: float = 30.0


# ============================================================
# Preset configurations per §3.8
# ============================================================


CIRCUIT_BREAKER_PRESETS: dict[str, CircuitBreakerConfig] = {
    "ss01_anchor":       CircuitBreakerConfig(5,  60, 30),
    "ss02_memory":       CircuitBreakerConfig(10, 60, 60),
    "ss03_emotion":      CircuitBreakerConfig(5,  60, 30),
    "ss04_relationship": CircuitBreakerConfig(5,  60, 30),
    "ss05_composer":     CircuitBreakerConfig(5,  60, 30),
    "ss06_inner_state":  CircuitBreakerConfig(5,  60, 30),
    "main_llm":          CircuitBreakerConfig(5,  60, 30),
    "cheap_llm":         CircuitBreakerConfig(5,  60, 30),
    "memory_encoder":    CircuitBreakerConfig(5,  120, 60),
    "critic":            CircuitBreakerConfig(5,  60, 30),
    "wellbeing":         CircuitBreakerConfig(3,  120, 60),
    "event_bus":         CircuitBreakerConfig(5,  60, 30),
    "session_manager":   CircuitBreakerConfig(5,  60, 30),
}


# ============================================================
# Circuit Breaker
# ============================================================


@dataclass
class CircuitBreakerSnapshot:
    """Immutable snapshot of breaker state — for observability."""
    name: str
    state: CircuitState
    failure_count: int
    total_calls: int
    total_failures: int
    opened_at: Optional[float] = None


class CircuitBreaker:
    """Per-subsystem circuit breaker (in-memory).

    Three-state model per §4.3:

        CLOSED ──(failures >= threshold)──► OPEN
          ▲                                  │
          │                                  │ (open_duration elapsed)
          │                                  ▼
          └──(probe succeeds)── HALF_OPEN ◄──┘
                 ▲                │
                 └──(probe fails)──┘

    Properties:
    - Failure window: rolling window, resets when window passes.
    - Half-open: allows exactly one probe call. Success → CLOSED, failure → OPEN.
    - Thread-safe: uses monotonic clock, but not internally locked (assumes
      single-event-loop async usage).
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Create a circuit breaker.

        Args:
            name: Unique service name for this breaker (e.g. "main_llm").
            config: Breaker config; defaults to CircuitBreakerConfig().
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state: CircuitState = CircuitState.CLOSED
        # Internal counters
        self._failure_count: int = 0
        self._window_start: float = 0.0
        self._opened_at: float = 0.0
        self._total_calls: int = 0
        self._total_failures: int = 0

    # --- Public API ---

    def is_open(self) -> bool:
        """Check if the circuit is currently open (rejecting calls).

        Side-effect: if OPEN duration has elapsed, transitions to HALF_OPEN.
        """
        if self.state == CircuitState.CLOSED:
            return False

        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.config.open_duration_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit [{self.name}] → HALF_OPEN "
                    f"(open for {elapsed:.1f}s, threshold={self.config.open_duration_seconds}s)"
                )
                return False
            return True

        # HALF_OPEN: allow probe calls through
        return False

    def record_success(self) -> None:
        """Record a successful call.

        If in HALF_OPEN, transitions back to CLOSED (probe succeeded).
        """
        self._total_calls += 1

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info(f"Circuit [{self.name}] → CLOSED (probe succeeded)")

    def record_failure(self) -> None:
        """Record a failed call.

        Increments failure counter; opens the circuit if threshold exceeded
        in the current window.
        """
        self._total_calls += 1
        self._total_failures += 1

        now = time.monotonic()

        # Reset window if expired
        if now - self._window_start > self.config.window_seconds:
            self._failure_count = 0
            self._window_start = now

        self._failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            # Probe failed — reopen immediately
            self.state = CircuitState.OPEN
            self._opened_at = now
            logger.warning(
                f"Circuit [{self.name}] → OPEN (half-open probe failed)"
            )
        elif (
            self.state == CircuitState.CLOSED
            and self._failure_count >= self.config.failure_threshold
        ):
            self.state = CircuitState.OPEN
            self._opened_at = now
            logger.warning(
                f"Circuit [{self.name}] → OPEN "
                f"({self._failure_count} failures in {self.config.window_seconds}s window)"
            )

    def reset(self) -> None:
        """Force-reset the breaker to CLOSED (for testing / manual intervention)."""
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._window_start = 0.0
        self._opened_at = 0.0
        logger.info(f"Circuit [{self.name}] manually reset → CLOSED")

    def stats(self) -> dict[str, Any]:
        """Return current breaker stats for monitoring (per §10.5)."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "window_start": self._window_start,
            "opened_at": self._opened_at if self.state == CircuitState.OPEN else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "window_seconds": self.config.window_seconds,
                "open_duration_seconds": self.config.open_duration_seconds,
            },
        }

    def snapshot(self) -> CircuitBreakerSnapshot:
        """Return an immutable snapshot of the breaker state."""
        return CircuitBreakerSnapshot(
            name=self.name,
            state=self.state,
            failure_count=self._failure_count,
            total_calls=self._total_calls,
            total_failures=self._total_failures,
            opened_at=self._opened_at if self.state == CircuitState.OPEN else None,
        )


# ============================================================
# FailureHandler — per §3.8
# ============================================================


# Fallback strategies per subsystem (spec §3.8)
FALLBACK_STRATEGIES: dict[str, str] = {
    "ss01_anchor":       "use_cached_anchor",
    "ss02_memory":       "use_l4_only",
    "ss03_emotion":      "use_neutral_state",
    "ss04_relationship": "use_last_known_stage",
    "ss06_inner_state":  "use_baseline_state",
    "main_llm":          "use_soul_flavored_fallback",
    "cheap_llm":         "use_soul_flavored_fallback",
}


class FailureHandler:
    """Cascade failure protection per §3.8.

    Wraps subsystem calls with circuit breaker + fallback. Each subsystem
    has an independent breaker with its own threshold/window/open_duration.

    Usage::

        handler = FailureHandler()
        handler.register("main_llm", CircuitBreakerConfig(5, 60, 30))

        result = await handler.with_circuit_breaker(
            "main_llm",
            func=lambda: call_llm(prompt),
            fallback=lambda: "……让我整理一下思绪。",
        )
    """

    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def register(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Register a circuit breaker for a service.

        Args:
            service_name: Unique name (e.g. "main_llm", "ss01_anchor").
            config: Breaker config; falls back to CIRCUIT_BREAKER_PRESETS.

        Returns:
            The registered CircuitBreaker instance.
        """
        if config is None:
            config = CIRCUIT_BREAKER_PRESETS.get(service_name)
        breaker = CircuitBreaker(service_name, config)
        self.breakers[service_name] = breaker
        return breaker

    def get(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get the breaker for a service, or None."""
        return self.breakers.get(service_name)

    async def with_circuit_breaker(
        self,
        service_name: str,
        func: Any,
        fallback: Any,
        timeout: Optional[float] = None,
    ) -> Any:
        """Execute func with circuit breaker protection.

        If the circuit is OPEN, fallback is called immediately.
        If func raises, the failure is recorded and fallback is invoked.

        Args:
            service_name: Registered service name.
            func: Primary callable (sync or async).
            fallback: Fallback callable (sync or async).
            timeout: Optional timeout in seconds.

        Returns:
            Result of func() or fallback().

        Raises:
            RuntimeError: if service_name is not registered.
        """
        import asyncio

        breaker = self.breakers.get(service_name)
        if breaker is None:
            raise RuntimeError(
                f"Circuit breaker not registered for '{service_name}'. "
                f"Call handler.register('{service_name}') first."
            )

        # Circuit OPEN → immediate fallback
        if breaker.is_open():
            logger.warning(f"Circuit [{service_name}] OPEN — using fallback")
            if asyncio.iscoroutinefunction(fallback):
                return await fallback()
            return fallback()

        try:
            if timeout is not None:
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(func(), timeout=timeout)
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(func), timeout=timeout
                    )
            else:
                if asyncio.iscoroutinefunction(func):
                    result = await func()
                else:
                    result = func()

            breaker.record_success()
            return result

        except Exception as e:
            breaker.record_failure()
            logger.error(f"Service [{service_name}] failed: {e}", exc_info=True)
            if asyncio.iscoroutinefunction(fallback):
                return await fallback()
            return fallback()

    def all_stats(self) -> dict[str, dict[str, Any]]:
        """Return stats for all registered breakers (for monitoring)."""
        return {name: cb.stats() for name, cb in self.breakers.items()}

    def all_snapshots(self) -> dict[str, CircuitBreakerSnapshot]:
        """Return snapshots for all registered breakers."""
        return {name: cb.snapshot() for name, cb in self.breakers.items()}
