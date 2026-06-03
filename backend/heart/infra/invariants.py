"""
State Invariant Verification Framework — per docs/design/state_invariants.md.

Layer 2: Runtime invariant assertions via @invariant decorator.
Layer 1 tests live in backend/tests/properties/.

Author: Heart Platform
"""

from __future__ import annotations

import functools
import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger(__name__)

# ── Prometheus metrics ───────────────────────────────────────────

INVARIANT_CHECK_TOTAL = Counter(
    "heart_invariant_check_total",
    "Invariant checks by ID, result, and severity",
    ["id", "result", "severity"],
)
INVARIANT_VIOLATIONS_TOTAL = Counter(
    "heart_invariant_violations_total",
    "Invariant violations by name and severity",
    ["name", "severity"],
)
INVARIANT_CHECK_DURATION = Histogram(
    "heart_invariant_check_duration_seconds",
    "Invariant check duration by ID",
    ["id"],
)


# ── Severity ─────────────────────────────────────────────────────


class Severity(str, Enum):
    FATAL = "FATAL"
    WARN = "WARN"


# ── Invariant mode ───────────────────────────────────────────────


class InvariantMode(str, Enum):
    """Behaviour modes for invariant checking."""

    ALWAYS = "always"
    DEV = "dev"
    SAMPLED = "sampled"
    OFF = "off"


def _resolve_mode() -> InvariantMode:
    """Resolve the current invariant checking mode from env."""
    explicit = os.environ.get("HEART_INVARIANTS", "").strip().lower()
    if explicit == "always":
        return InvariantMode.ALWAYS
    if explicit == "off":
        return InvariantMode.OFF
    env_val = os.environ.get("HEART_ENV", "dev").strip().lower()
    if env_val == "prod":
        return InvariantMode.SAMPLED
    return InvariantMode.DEV


# Always-on safety invariant IDs (forced to ALWAYS regardless of env).
ALWAYS_ON_SAFETY_IDS: frozenset[str] = frozenset(
    {
        "inv-o-2.message-severity-cap",
        "inv-o-3.purple-blocked-from-soul",
        "inv-o-5.no-raw-sdk-leak",
    }
)


def _sample_decision(trace_id: str, rate: float = 0.01) -> bool:
    """Deterministic sampling via hash of trace_id.

    Same trace_id always produces the same decision, keeping
    consistency within a single multi-invariant turn.
    """
    digest = hashlib.md5(trace_id.encode()).digest()
    val = (digest[0] << 8 | digest[1]) / 65536.0
    return val < rate


# ── InvariantViolation ───────────────────────────────────────────


class InvariantViolation(Exception):
    """Raised for FATAL invariant violations in DEV/TEST mode."""

    def __init__(
        self,
        invariant_id: str,
        severity: Severity,
        details: Dict[str, Any],
    ):
        self.invariant_id = invariant_id
        self.severity = severity
        self.details = details
        super().__init__(f"Invariant {invariant_id} ({severity.value}) violated: {details}")


# ── InvariantRecord ──────────────────────────────────────────────


@dataclass
class InvariantRecord:
    """Metadata for one registered invariant."""

    id: str
    name: str
    subsystem: str
    severity: Severity
    predicate: Callable[..., bool]
    extract_state: Optional[Callable[..., Any]] = None
    doc: str = ""


# ── InvariantRegistry ────────────────────────────────────────────


class InvariantRegistry:
    """Singleton registry for all Layer-2 invariants."""

    _instance: Optional[InvariantRegistry] = None

    def __init__(self):
        self._invariants: Dict[str, InvariantRecord] = {}
        self._mode: InvariantMode = _resolve_mode()

    @classmethod
    def instance(cls) -> InvariantRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (primarily for testing)."""
        if cls._instance is not None:
            cls._instance._invariants.clear()
            cls._instance = None

    def register(
        self,
        *,
        id: str,
        name: str = "",
        subsystem: str = "",
        severity: Severity = Severity.WARN,
        predicate: Callable[..., bool],
        extract_state: Optional[Callable[..., Any]] = None,
        doc: str = "",
    ) -> None:
        """Register an invariant definition."""
        if id in self._invariants:
            logger.warning("invariant_already_registered", id=id)
            return
        self._invariants[id] = InvariantRecord(
            id=id,
            name=name or id,
            subsystem=subsystem,
            severity=severity,
            predicate=predicate,
            extract_state=extract_state,
            doc=doc,
        )
        logger.debug("invariant_registered", id=id, severity=severity.value)

    def get(self, id: str) -> Optional[InvariantRecord]:
        return self._invariants.get(id)

    def list_all(self) -> List[InvariantRecord]:
        return list(self._invariants.values())

    def should_check(self, invariant_id: str, trace_id: str = "") -> bool:
        """Return True if this invariant should be checked right now."""
        mode = self._mode
        if invariant_id.lower() in ALWAYS_ON_SAFETY_IDS:
            mode = InvariantMode.ALWAYS
        if mode == InvariantMode.ALWAYS or mode == InvariantMode.DEV:
            return True
        if mode == InvariantMode.OFF:
            return False
        # SAMPLED mode
        if not trace_id:
            return False
        return _sample_decision(trace_id)


# ── Invariant context helper ─────────────────────────────────────


@dataclass
class InvariantContext:
    """Bundled state passed to check_invariants.

    All fields are optional — predicates should be defensive.
    """

    user_id: Optional[str] = None
    character_id: Optional[str] = None
    trace_id: Optional[str] = None
    before_state: Optional[Any] = None
    after_state: Optional[Any] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# ── check_invariants ─────────────────────────────────────────────


def check_invariants(
    ctx: InvariantContext,
    *,
    ids: Optional[Sequence[str]] = None,
) -> Dict[str, bool]:
    """Run all registered invariants (or a subset) against a context.

    Returns a dict mapping invariant ID to pass/fail.
    In DEV/TEST: FATAL violations raise InvariantViolation.
    In PROD: FATAL violations are logged and return False; never raise.
    """
    registry = InvariantRegistry.instance()
    trace_id = ctx.trace_id or ""
    candidates = (
        [registry.get(iid) for iid in ids if registry.get(iid)]
        if ids is not None
        else registry.list_all()
    )
    results: Dict[str, bool] = {}
    for record in candidates:
        if not record:
            continue
        check_id = record.id

        # Sampling gate
        if not registry.should_check(check_id, trace_id):
            INVARIANT_CHECK_TOTAL.labels(
                id=check_id, result="skipped", severity=record.severity.value
            ).inc()
            continue

        # Evaluate
        INVARIANT_CHECK_TOTAL.labels(
            id=check_id, result="check", severity=record.severity.value
        ).inc()
        try:
            passed = record.predicate(ctx)
        except Exception:
            logger.exception("invariant_predicate_error", id=check_id)
            passed = False  # Treat predicate errors as violations

        if passed:
            INVARIANT_CHECK_TOTAL.labels(
                id=check_id, result="ok", severity=record.severity.value
            ).inc()
            results[check_id] = True
        else:
            # Violation
            INVARIANT_VIOLATIONS_TOTAL.labels(
                name=record.name, severity=record.severity.value
            ).inc()
            INVARIANT_CHECK_TOTAL.labels(
                id=check_id, result="violation", severity=record.severity.value
            ).inc()

            # Structured log
            logger.warning(
                "invariant_violation",
                id=check_id,
                name=record.name,
                severity=record.severity.value,
                subsystem=record.subsystem,
                user_id=ctx.user_id,
                character_id=ctx.character_id,
                trace_id=ctx.trace_id,
            )
            results[check_id] = False

            # FATAL handling
            if record.severity == Severity.FATAL:
                mode = registry._mode
                if mode in (InvariantMode.ALWAYS, InvariantMode.DEV):
                    raise InvariantViolation(
                        invariant_id=check_id,
                        severity=record.severity,
                        details={"user_id": ctx.user_id, "trace_id": ctx.trace_id},
                    )

    return results


# ── @invariant decorator ─────────────────────────────────────────


def invariant(
    name: str,
    *,
    predicate: Optional[Callable[..., bool]] = None,
    severity: Severity = Severity.WARN,
    subsystem: str = "",
    doc: str = "",
) -> Callable:
    """Decorator that registers the invariant and optionally wraps a service method.

    Two usage styles:

    1. Registration only (used from Hypothesis tests):
       @invariant("inv-m-1.l1-subset-l2", predicate=my_pred, severity=Severity.FATAL)

    2. Method wrapper (auto-checks before/after):
       @invariant("inv-e-2.vad-range", severity=Severity.WARN)
       def transition(self, state):
           ...

    When used as a method wrapper, the decorator captures:
      - before: extract_state(*args, **kwargs) if provided, else args[0]
      - after:  extract_state(result) if provided, else result
    and calls the predicate with a context.
    """
    registry = InvariantRegistry.instance()

    # Style 1: Registration-only (predicate is passed explicitly, not wrapping anything)
    if predicate is not None:
        registry.register(
            id=name,
            name=name,
            subsystem=subsystem,
            severity=severity,
            predicate=predicate,
            doc=doc,
        )
        return predicate

    # Style 2: Decorator factory — will be called on a function
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace_id = _extract_trace_id(*args, **kwargs)
            before = _capture_before(name, args, kwargs)
            result = func(*args, **kwargs)
            after = _capture_after(name, result)

            record = registry.get(name)
            if record is not None and record.predicate is not None:
                ctx = InvariantContext(
                    user_id=_extract_user_id(*args, **kwargs),
                    character_id=_extract_character_id(*args, **kwargs),
                    trace_id=trace_id,
                    before_state=before,
                    after_state=after,
                )
                if registry.should_check(name, trace_id):
                    try:
                        passed = record.predicate(ctx)
                        INVARIANT_CHECK_TOTAL.labels(
                            id=name,
                            result="ok" if passed else "violation",
                            severity=record.severity.value,
                        ).inc()
                        if not passed:
                            INVARIANT_VIOLATIONS_TOTAL.labels(
                                name=record.name,
                                severity=record.severity.value,
                            ).inc()
                            logger.warning(
                                "invariant_violation",
                                id=name,
                                name=record.name,
                                severity=record.severity.value,
                                subsystem=record.subsystem,
                                user_id=ctx.user_id,
                                character_id=ctx.character_id,
                                trace_id=ctx.trace_id,
                            )
                            if record.severity == Severity.FATAL:
                                mode = registry._mode
                                if mode in (InvariantMode.ALWAYS, InvariantMode.DEV):
                                    raise InvariantViolation(
                                        invariant_id=name,
                                        severity=record.severity,
                                        details={
                                            "user_id": ctx.user_id,
                                            "trace_id": ctx.trace_id,
                                        },
                                    )
                    except InvariantViolation:
                        raise
                    except Exception:
                        logger.exception("invariant_predicate_error", id=name)
            return result

        return wrapper

    return decorator


# ── Internal helpers for @invariant decorator ────────────────────


def _extract_trace_id(*args, **kwargs) -> str:
    """Walk args/kwargs to find a trace_id."""
    for key in ("trace_id", "turn_id"):
        val = kwargs.get(key)
        if val is not None:
            return str(val)
    for arg in args:
        if isinstance(arg, str) and len(arg) > 8:
            return str(arg)
    return ""


def _extract_user_id(*args, **kwargs) -> Optional[str]:
    val = kwargs.get("user_id")
    if val is not None:
        return str(val)
    for arg in args:
        if hasattr(arg, "user_id"):
            return str(arg.user_id)
    return None


def _extract_character_id(*args, **kwargs) -> Optional[str]:
    val = kwargs.get("character_id")
    if val is not None:
        return str(val)
    for arg in args:
        if hasattr(arg, "character_id"):
            return str(arg.character_id)
    return None


def _capture_before(invariant_id: str, args: tuple, kwargs: dict) -> Any:
    record = InvariantRegistry.instance().get(invariant_id)
    if record and record.extract_state:
        return record.extract_state(*args, **kwargs)
    if args:
        return args[0]
    return kwargs


def _capture_after(invariant_id: str, result: Any) -> Any:
    record = InvariantRegistry.instance().get(invariant_id)
    if record and record.extract_state:
        return record.extract_state(result)
    return result
