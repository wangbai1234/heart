"""
SS07 Orchestration — Invariant sampling middleware per §4.3 of state_invariants.md.

Runs all registered invariants at a configurable sample rate on every turn
processed by the orchestrator.

Author: Heart Platform
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable
from uuid import UUID

import structlog

from heart.infra.invariants import (
    InvariantContext,
    InvariantRegistry,
    check_invariants,
)

logger = structlog.get_logger(__name__)


async def orchestrate_with_invariants(
    *,
    user_id: UUID,
    character_id: str,
    message: str,
    turn_id: UUID,
    inner_fn: Callable[[], Any],
    sampling_rate: float = 0.01,
) -> Any:
    """Orchestrator hot-path wrapper that samples invariant checking.

    Args:
        user_id: Current user UUID.
        character_id: Current character identifier.
        message: Raw user message.
        turn_id: Current turn UUID (doubles as trace_id for sampling hash).
        inner_fn: The actual turn-processing function to invoke.
        sampling_rate: Fraction of turns to sample in PROD (default 1%).

    Returns:
        Whatever the inner_fn returns.
    """
    registry = InvariantRegistry.instance()
    trace_id = str(turn_id)
    should_sample = registry.should_check("_any_", trace_id)

    # Execute the inner turn-processing function
    t0 = time.monotonic()
    if inspect.iscoroutinefunction(inner_fn):
        result = await inner_fn()
    else:
        result = inner_fn()
    elapsed = time.monotonic() - t0

    # Run invariants only in non-OFF mode, and only when sampled
    if should_sample:
        ctx = InvariantContext(
            user_id=str(user_id),
            character_id=character_id,
            trace_id=trace_id,
            after_state=result,
        )
        try:
            outcomes = check_invariants(ctx)
            violation_ids = [iid for iid, passed in outcomes.items() if not passed]
            if violation_ids:
                logger.warning(
                    "orchestrator_invariant_violations",
                    turn_id=trace_id,
                    user_id=str(user_id),
                    violation_count=len(violation_ids),
                    violations=violation_ids,
                    turn_duration_ms=int(elapsed * 1000),
                )
        except Exception:
            # Invariant checking must never break the turn in production
            logger.error("orchestrator_invariant_check_failed", turn_id=trace_id)

    return result
