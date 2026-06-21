"""
SS04 Special States — DRIFTING / COLD_WAR / RECONCILING / REUNION

Per runtime_specs/04_relationship_phase_engine.md §3.1 Special States.

These are overlay states on top of the normal Stage progression.
They modify behavior but don't change the underlying Stage (except COLD_WAR > 14 days).

Author: 心屿团队
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class SpecialState(str, Enum):
    """Special relationship states (overlay on Stage)."""

    NONE = "none"
    COLD_WAR = "cold_war"
    DRIFTING = "drifting"
    RECONCILING = "reconciling"
    REUNION = "reunion"


def evaluate_special_state(
    current_states: list[dict[str, Any]],
    signals: Any,
    days_since_last: float,
    emotion_state: Optional[dict] = None,
) -> Optional[SpecialState]:
    """Evaluate whether to enter/exit a special state.

    Args:
        current_states: Current active_special_states from RelationshipState
        signals: Turn signals (from SignalAggregator or raw)
        days_since_last: Days since last interaction
        emotion_state: Current emotion state dict (for coldness detection)

    Returns:
        New SpecialState if transition needed, None to keep current.
    """
    # Get current special state (if any)
    current = _get_current_special(current_states)

    # Extract signal attributes safely
    coldness_intensity = _get_coldness_intensity(emotion_state)
    repair_progress = _get_repair_progress(emotion_state)
    warmth_count = _get_attr(signals, "warmth_signal_count", 0)

    # ── COLD_WAR: enter ──
    # Trigger: coldness > 0.5 and repair_required
    if current == SpecialState.NONE and coldness_intensity > 0.5:
        logger.info("special_state_enter", state="cold_war", coldness=coldness_intensity)
        return SpecialState.COLD_WAR

    # ── COLD_WAR: exit → RECONCILING or NONE ──
    if current == SpecialState.COLD_WAR:
        # Exit if repair_progress > 0.6 → RECONCILING
        if repair_progress > 0.6:
            logger.info("special_state_exit", from_state="cold_war", to_state="reconciling")
            return SpecialState.RECONCILING
        # Exit if coldness dropped below threshold
        if coldness_intensity < 0.3:
            logger.info("special_state_exit", from_state="cold_war", to_state="none")
            return SpecialState.NONE
        # Stay in COLD_WAR
        return None

    # ── DRIFTING: enter ──
    # Trigger: absence > 14 days
    if current == SpecialState.NONE and days_since_last > 14:
        logger.info("special_state_enter", state="drifting", days_since_last=days_since_last)
        return SpecialState.DRIFTING

    # ── DRIFTING: exit → REUNION or NONE ──
    if current == SpecialState.DRIFTING:
        # User returned after > 7 days absence → REUNION
        if days_since_last <= 1 and _get_total_interactions(signals) > 0:
            logger.info("special_state_exit", from_state="drifting", to_state="reunion")
            return SpecialState.REUNION
        # Absence > 30 days → might trigger stage regression (handled by stage engine)
        return None

    # ── RECONCILING: exit → NONE after warm interactions ──
    if current == SpecialState.RECONCILING:
        if warmth_count >= 2 or repair_progress > 0.8:
            logger.info("special_state_exit", from_state="reconciling", to_state="none")
            return SpecialState.NONE
        return None

    # ── REUNION: exit → NONE after settling ──
    if current == SpecialState.REUNION:
        reunion_turns = _get_reunion_turns(current_states)
        if reunion_turns >= 10:
            logger.info("special_state_exit", from_state="reunion", to_state="none")
            return SpecialState.NONE
        return None

    return None


def advance_reunion_turn(current_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Increment reunion turn counter. Called each turn during REUNION state."""
    for state in current_states:
        if state.get("state") == SpecialState.REUNION.value:
            state["turns_in_state"] = state.get("turns_in_state", 0) + 1
    return current_states


def _get_current_special(states: list[dict[str, Any]]) -> SpecialState:
    """Get the current active special state (if any)."""
    for s in states:
        state_val = s.get("state", "none")
        if state_val != "none":
            try:
                return SpecialState(state_val)
            except ValueError:
                continue
    return SpecialState.NONE


def _get_coldness_intensity(emotion_state: Optional[dict]) -> float:
    """Extract coldness intensity from emotion state."""
    if not emotion_state:
        return 0.0
    active = emotion_state.get("active_stack", [])
    for e in active:
        if e.get("emotion") == "coldness":
            return e.get("intensity", 0.0)
    return 0.0


def _get_repair_progress(emotion_state: Optional[dict]) -> float:
    """Extract repair progress from emotion state."""
    if not emotion_state:
        return 0.0
    return emotion_state.get("repair_progress", 0.0)


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from object or dict."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _get_total_interactions(signals: Any) -> int:
    """Get total interaction count from signals."""
    return _get_attr(signals, "total_interactions", 0)


def _get_reunion_turns(states: list[dict[str, Any]]) -> int:
    """Get turn count in current REUNION state."""
    for s in states:
        if s.get("state") == SpecialState.REUNION.value:
            return s.get("turns_in_state", 0)
    return 0
