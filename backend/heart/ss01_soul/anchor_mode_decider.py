"""
Anchor Mode Decider - SS01 Soul Spec

Decides which AnchorMode (FULL/LIGHT) to inject per turn, per:
runtime_specs/01_identity_anchor_soul_spec.md §3.4

Cadence (per §3.4):
    turn 1:           FULL  (first contact)
    turn 2-7:         LIGHT
    turn 8:           FULL  (periodic re-injection)
    turn 9-15:        LIGHT
    ...

Special triggers (early FULL injection):
    - drift_score > 0.3

REINFORCE is NOT decided here. REINFORCE requires DriftEvidence from
the Drift Detector and is selected by the orchestrator when evidence
is available.

Author: 心屿团队
"""

from __future__ import annotations

from .anchor_injector import AnchorActivationView, AnchorMode

# Periodic FULL re-injection interval (turns).
# §3.4 example table shows turn 1 → turn 8 (gap 7). Honoring that
# value; downstream tweaks should adjust this constant.
_FULL_REINJECTION_INTERVAL = 7

# Drift score threshold for early FULL injection per §3.4.
_DRIFT_FULL_THRESHOLD = 0.3


def decide_mode(
    activation_state: AnchorActivationView,
    turn_index: int,
    drift_score: float,
) -> AnchorMode:
    """Decide AnchorMode per §3.4 cadence rules.

    Rules in priority order:
        1. drift_score > 0.3            → FULL (special early-injection)
        2. turn_index <= 1              → FULL (first contact)
        3. turn_index - last_full >= 7  → FULL (periodic re-injection)
        4. else                         → LIGHT

    Args:
        activation_state: Per-(user, character) state projection.
        turn_index: Current turn number (1-indexed).
        drift_score: Current drift score in [0, 1].

    Returns:
        AnchorMode.FULL or AnchorMode.LIGHT.

    Note:
        REINFORCE is not returned by this function. It is selected by
        the orchestrator when DriftEvidence is available from the
        async Drift Detector path (§3.6).
    """
    if drift_score > _DRIFT_FULL_THRESHOLD:
        return AnchorMode.FULL

    if turn_index <= 1:
        return AnchorMode.FULL

    turns_since_full = turn_index - activation_state.last_full_anchor_turn
    if turns_since_full >= _FULL_REINJECTION_INTERVAL:
        return AnchorMode.FULL

    return AnchorMode.LIGHT
