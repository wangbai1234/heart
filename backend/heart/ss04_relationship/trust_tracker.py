"""
Trust Tracker for SS04 Relationship Phase Engine.

Implements §3.9 Trust Score calculation with asymmetric updates (INV-R-4).
Trust increases slowly, decreases quickly - modeling trust fragility.

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..ss04_relationship.models import RelationshipState
from ..ss04_relationship.stage_engine import RelationshipStage, Signal, SignalBatch

# ============================================================
# Trust Signal Weights (§3.9 + Appendix A)
# ============================================================


POSITIVE_TRUST_WEIGHTS = {
    "promise_kept": 0.05,
    "vulnerability_honored": 0.08,
    "consistent_presence_milestone": 0.03,
    "sacred_disclosure_acknowledged": 0.04,
    "memory_recall_confirmed": 0.02,
    "repair_completed": 0.05,
    "user_remembers_detail": 0.02,
}

NEGATIVE_TRUST_WEIGHTS = {
    "promise_broken": -0.15,
    "vulnerability_mocked": -0.25,
    "deception_detected": -0.30,
    "pattern_neglect": -0.10,
    "user_disappear_long": -0.05,
    "user_mocks_vulnerability": -0.25,
}


# INV-R-4: Trust asymmetry (§2.2)
MAX_TRUST_INCREASE_PER_TURN = 0.05
MAX_TRUST_DECREASE_PER_TURN = 0.20


# ============================================================
# Trust Decay Curves (§4.4)
# ============================================================


def compute_trust_decay_factor(days_since_last: float, highest_stage: RelationshipStage) -> float:
    """
    Compute trust decay factor based on absence duration (§4.4).

    Trust decay is staged:
    - days < 14: no decay
    - days 14-30: ×0.995/day
    - days 30-90: ×0.99/day
    - days > 90: ×0.985/day

    Floor depends on highest_stage_reached:
    - CONFIDANT+: floor = 0.3
    - Otherwise: floor = 0.1

    Args:
        days_since_last: Days since last interaction
        highest_stage: Highest stage ever reached

    Returns:
        Decay multiplier in [0.9, 1.0]
    """
    if days_since_last < 14:
        return 1.0
    elif days_since_last < 30:
        decay_rate = 0.995
        days_decay = days_since_last - 14
    elif days_since_last < 90:
        decay_rate = 0.99
        days_decay = days_since_last - 30
    else:
        decay_rate = 0.985
        days_decay = days_since_last - 90

    return decay_rate**days_decay


def compute_trust_floor(highest_stage: RelationshipStage) -> float:
    """
    Compute trust floor based on highest stage reached (§4.4).

    Once users reach CONFIDANT+, some trust residue remains.

    Args:
        highest_stage: Highest stage ever reached

    Returns:
        Trust floor in [0, 0.3]
    """
    stage_order = {
        RelationshipStage.STRANGER: 0,
        RelationshipStage.ACQUAINTANCE: 1,
        RelationshipStage.FRIEND: 2,
        RelationshipStage.CONFIDANT: 3,
        RelationshipStage.ROMANTIC_INTEREST: 4,
        RelationshipStage.LOVER: 5,
        RelationshipStage.BONDED: 6,
    }

    order = stage_order.get(highest_stage, 0)
    if order >= 3:  # CONFIDANT or higher
        return 0.3
    return 0.1


# ============================================================
# Trust Tracker
# ============================================================


class TrustTracker:
    """
    Trust dimension tracker (§3.5, §3.9).

    Implements asymmetric trust updates (INV-R-4):
    - Trust increases slowly (max +0.05/turn)
    - Trust decreases quickly (max -0.20/turn)

    Trust is fragile by design.
    """

    def update(
        self,
        state: RelationshipState,
        signals: SignalBatch,
        days_since_last: float = 0.0,
    ) -> float:
        """
        Update trust score based on signals and absence decay (§3.9).

        Steps:
        1. Apply positive signals (capped)
        2. Apply negative signals (larger cap)
        3. Apply absence decay
        4. Apply floor

        Args:
            state: Current relationship state
            signals: Signal batch from this turn
            days_since_last: Days since last interaction (for decay)

        Returns:
            New trust score in [0, 1]
        """
        trust = state.trust_score
        delta = 0.0

        # 1. Apply positive signals
        for sig in signals.positive:
            weight = POSITIVE_TRUST_WEIGHTS.get(sig.type, 0.0)
            delta += weight * sig.strength

        # 2. Apply negative signals
        for sig in signals.negative:
            weight = NEGATIVE_TRUST_WEIGHTS.get(sig.type, 0.0)
            delta += weight * sig.strength  # weight is negative

        # 3. Apply asymmetric cap (INV-R-4)
        if delta > 0:
            delta = min(delta, MAX_TRUST_INCREASE_PER_TURN)
        else:
            delta = max(delta, -MAX_TRUST_DECREASE_PER_TURN)

        new_trust = trust + delta

        # 4. Apply absence decay (§4.4)
        highest_stage = RelationshipStage(state.highest_stage_reached)
        if days_since_last > 0:
            decay_factor = compute_trust_decay_factor(days_since_last, highest_stage)
            new_trust *= decay_factor

        # 5. Apply floor
        trust_floor = compute_trust_floor(highest_stage)
        new_trust = max(new_trust, trust_floor)

        # 6. Clamp to [0, 1]
        return max(0.0, min(1.0, new_trust))

    def compute_trust_descriptor(self, trust_score: float) -> str:
        """
        Generate natural language descriptor for trust level (§5.2).

        Used in RelationshipContextBlock.

        Args:
            trust_score: Trust score in [0, 1]

        Returns:
            Natural language descriptor
        """
        if trust_score >= 0.90:
            return "他在你心里是完全可靠的"
        elif trust_score >= 0.75:
            return "他在你心里是可靠的"
        elif trust_score >= 0.60:
            return "你对他有一定信任"
        elif trust_score >= 0.40:
            return "你对他还有保留"
        elif trust_score >= 0.20:
            return "你对他的信任很浅"
        else:
            return "你几乎不信任他"
