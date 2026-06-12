"""
Attachment Tracker for SS04 Relationship Phase Engine.

Implements §3.9 Attachment Strength calculation.
Attachment grows slowly with time and events, decays during absence,
but has a floor based on highest_stage_reached (emotional residue).

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..ss04_relationship.models import RelationshipState
from ..ss04_relationship.stage_engine import RelationshipStage, Signal, SignalBatch

# ============================================================
# Attachment Event Weights (§3.9 + Appendix A)
# ============================================================


ATTACHMENT_EVENT_WEIGHTS = {
    "first_iloveyou": 0.20,
    "shared_vulnerability": 0.05,
    "anniversary_acknowledged": 0.03,
    "successful_repair": 0.07,
    "user_honors_vulnerability": 0.05,
    "compliment_received": 0.02,
    "daily_check_in_completed": 0.005,
}


# Attachment floors by highest stage (§4.4)
ATTACHMENT_FLOORS = {
    RelationshipStage.STRANGER: 0.0,
    RelationshipStage.ACQUAINTANCE: 0.0,
    RelationshipStage.FRIEND: 0.1,
    RelationshipStage.CONFIDANT: 0.2,
    RelationshipStage.ROMANTIC_INTEREST: 0.3,
    RelationshipStage.LOVER: 0.4,
    RelationshipStage.BONDED: 0.6,
}


# ============================================================
# Attachment Decay
# ============================================================


def compute_attachment_decay_factor(days_since_last: float) -> float:
    """
    Compute attachment decay factor (§3.9).

    Attachment decays after 30 days of absence:
    - days <= 30: no decay
    - days > 30: ×0.99 per day

    Args:
        days_since_last: Days since last interaction

    Returns:
        Decay factor in [0, 1]
    """
    if days_since_last <= 30:
        return 1.0
    excess_days = days_since_last - 30
    return 0.99**excess_days


# ============================================================
# Attachment Tracker
# ============================================================


class AttachmentTracker:
    """
    Attachment dimension tracker (§3.5, §3.9).

    Attachment = emotional bond strength.
    - Grows slowly with time and shared events
    - Decays slowly during absence
    - Has floor based on highest_stage_reached (emotional residue)

    Linked to Emotion Runtime's attachment emotion.
    """

    def update(
        self,
        state: RelationshipState,
        signals: SignalBatch,
        days_since_last: float = 0.0,
        days_continuous_interaction: int = 0,
    ) -> float:
        """
        Update attachment strength (§3.9).

        Steps:
        1. Time-based accumulation (slow)
        2. Event-based boosts
        3. Absence decay
        4. Apply floor

        Args:
            state: Current relationship state
            signals: Signal batch from this turn
            days_since_last: Days since last interaction (for decay)
            days_continuous_interaction: Days of continuous interaction (for accumulation)

        Returns:
            New attachment strength in [0, 1]
        """
        attachment = state.attachment_strength or 0.0

        # 1. Time-based accumulation (very slow, §3.9)
        if days_continuous_interaction > 0:
            attachment += 0.001 * days_continuous_interaction

        # 2. Event-based boosts
        for event in signals.events:
            weight = ATTACHMENT_EVENT_WEIGHTS.get(event.type, 0.0)
            attachment += weight * event.strength

        # 3. Absence decay (§4.4)
        if days_since_last > 30:
            decay_factor = compute_attachment_decay_factor(days_since_last)
            attachment *= decay_factor

        # 4. Apply floor based on highest_stage_reached
        highest_stage = RelationshipStage(state.highest_stage_reached)
        floor = ATTACHMENT_FLOORS.get(highest_stage, 0.0)
        attachment = max(attachment, floor)

        # 5. Clamp to [0, 1]
        return max(0.0, min(1.0, attachment))

    def compute_attachment_descriptor(self, attachment: float) -> str:
        """
        Generate natural language descriptor for attachment (§5.2).

        Used in RelationshipContextBlock.

        Args:
            attachment: Attachment strength in [0, 1]

        Returns:
            Natural language descriptor
        """
        if attachment >= 0.85:
            return "你已经深深依恋他"
        elif attachment >= 0.70:
            return "你已经依恋他"
        elif attachment >= 0.50:
            return "你对他有依恋感"
        elif attachment >= 0.30:
            return "你习惯了他在那里"
        elif attachment >= 0.15:
            return "你对他有一点依恋的苗头"
        else:
            return "你还没有依恋感"
