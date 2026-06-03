"""
Stage Phase Engine for SS04 Relationship Phase Engine.

Implements §3.6 Stage Transition State Machine and §10.3 Core Algorithms.
Evaluates stage transitions (progression/regression) based on:
- Entry conditions (§3.7)
- Soul gates (from Soul Spec relational_template)
- Minimum time requirements
- Anti-gaming rules

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from heart.infra.invariants import invariant

import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip

from ..ss04_relationship.models import RelationshipState

# ============================================================
# Stage Enum
# ============================================================


class RelationshipStage(str, Enum):
    """7 core relationship stages (§3.1)."""

    STRANGER = "STRANGER"
    ACQUAINTANCE = "ACQUAINTANCE"
    FRIEND = "FRIEND"
    CONFIDANT = "CONFIDANT"
    ROMANTIC_INTEREST = "ROMANTIC_INTEREST"
    LOVER = "LOVER"
    BONDED = "BONDED"


STAGE_ORDER = {
    RelationshipStage.STRANGER: 0,
    RelationshipStage.ACQUAINTANCE: 1,
    RelationshipStage.FRIEND: 2,
    RelationshipStage.CONFIDANT: 3,
    RelationshipStage.ROMANTIC_INTEREST: 4,
    RelationshipStage.LOVER: 5,
    RelationshipStage.BONDED: 6,
}


# ============================================================
# Minimum Time Requirements (§3.7)
# ============================================================


MIN_DAYS_IN_STAGE = {
    RelationshipStage.STRANGER: 1,
    RelationshipStage.ACQUAINTANCE: 3,
    RelationshipStage.FRIEND: 7,
    RelationshipStage.CONFIDANT: 7,
    RelationshipStage.ROMANTIC_INTEREST: 14,
    RelationshipStage.LOVER: 60,
    RelationshipStage.BONDED: 0,  # Terminal stage
}


# ============================================================
# Signal Types
# ============================================================


@dataclass
class Signal:
    """Generic relationship signal."""

    type: str
    strength: float  # [0, 1]
    metadata: dict[str, Any]


@dataclass
class SignalBatch:
    """Aggregated signals for a turn (§3.5)."""

    positive: list[Signal]  # Trust-building signals
    negative: list[Signal]  # Trust-damaging signals
    events: list[Signal]  # Major events (L4 promotions, conflicts, repairs)


# ============================================================
# Transition Decision
# ============================================================


class TransitionAction(str, Enum):
    """Transition action result."""

    STAY = "stay"
    PROGRESS = "progress"
    REGRESS = "regress"


@dataclass
class StageDecision:
    """Result of stage transition evaluation (§10.3)."""

    action: TransitionAction
    to_stage: Optional[RelationshipStage] = None
    reason: str = ""
    blocked_by: Optional[str] = None  # Which gate/condition failed


# ============================================================
# Stage Phase Engine
# ============================================================


class StagePhaseEngine:
    """
    Core state machine for relationship stage transitions (§3.6).

    Evaluates progression and regression based on:
    - Entry conditions (§3.7)
    - Soul gates (character-specific progression curves)
    - Minimum time requirements
    - Anti-gaming rules

    INV-R-2: Every stage transition must pass all gates.
    """

    def __init__(self, soul_spec: dict[str, Any]):
        """
        Initialize with Soul Spec for character-specific gates.

        Args:
            soul_spec: Soul Spec YAML dict with relational_template
        """
        self.soul_spec = soul_spec
        self.relational_template = soul_spec.get("relational_template", {})
        self.intimacy_resistance = self.relational_template.get("intimacy_resistance", 0.5)
        self.vulnerability_thresholds = self.relational_template.get(
            "vulnerability_unlock_thresholds", []
        )

    @invariant("inv-r-6.cold-war-no-progress")
    @invariant("inv-r-4.trust-asymmetry")
    @invariant("inv-r-1.stage-monotonic")
    def evaluate(self, state: RelationshipState, signals: SignalBatch) -> StageDecision:
        """
        Evaluate stage transition for current turn (§3.5 step 5).

        Order (§10.3):
        1. Check regression first (safety)
        2. Check progression
        3. Default: stay

        Args:
            state: Current relationship state
            signals: Aggregated signals from this turn

        Returns:
            StageDecision with action and optional target stage
        """
        current_stage = RelationshipStage(state.current_stage)

        # 1. Check regression first (INV-R-2: regression is rare and gated)
        regression_decision = self._check_regression(state, signals, current_stage)
        if regression_decision.action == TransitionAction.REGRESS:
            return regression_decision

        # 2. Check progression
        progression_decision = self._check_progression(state, signals, current_stage)
        if progression_decision.action == TransitionAction.PROGRESS:
            return progression_decision

        # 3. Default: stay
        return StageDecision(
            action=TransitionAction.STAY,
            reason="No transition conditions met",
            blocked_by="no_conditions_met",
        )

    def _check_progression(
        self,
        state: RelationshipState,
        signals: SignalBatch,
        current_stage: RelationshipStage,
    ) -> StageDecision:
        """
        Check if progression to next stage is allowed (§3.7).

        Steps:
        1. Get next stage
        2. Check all hard requirements
        3. Check Soul gate
        4. Check minimum time
        5. Check anti-gaming

        Returns:
            StageDecision with PROGRESS or STAY
        """
        next_stage = self._get_next_stage(current_stage)
        if not next_stage:
            return StageDecision(
                action=TransitionAction.STAY,
                reason=f"Already at terminal stage: {current_stage}",
            )

        # Check hard requirements
        requirements_met, reason = self._check_entry_requirements(state, next_stage)
        if not requirements_met:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"entry_requirements: {reason}",
            )

        # Check Soul gate
        soul_gate_passes, reason = self._check_soul_gate(state, next_stage)
        if not soul_gate_passes:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"soul_gate: {reason}",
            )

        # Check minimum time
        time_satisfied, reason = self._check_minimum_time(state, current_stage)
        if not time_satisfied:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"minimum_time: {reason}",
            )

        # Check anti-gaming
        anti_gaming_passes, reason = self._check_anti_gaming(state, signals)
        if not anti_gaming_passes:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"anti_gaming: {reason}",
            )

        # All gates passed
        return StageDecision(
            action=TransitionAction.PROGRESS,
            to_stage=next_stage,
            reason=f"All conditions met for {next_stage}",
        )

    def _check_regression(
        self,
        state: RelationshipState,
        signals: SignalBatch,
        current_stage: RelationshipStage,
    ) -> StageDecision:
        """
        Check if stage should regress (§3.8).

        Regression is RARE and GATED (§3.3).
        Requires sustained negative signals.

        Returns:
            StageDecision with REGRESS or STAY
        """
        if current_stage == RelationshipStage.STRANGER:
            return StageDecision(action=TransitionAction.STAY, reason="Already at minimum stage")

        prev_stage = self._get_previous_stage(current_stage)
        if not prev_stage:
            return StageDecision(action=TransitionAction.STAY)

        # Calculate days since last interaction
        days_since_last = self._calculate_days_since_last(state)

        # Regression conditions per stage (§3.8)
        if current_stage == RelationshipStage.ACQUAINTANCE:
            if current_stage == RelationshipStage.FRIEND:
                # To ACQUAINTANCE from FRIEND
                if days_since_last > 60:
                    return StageDecision(
                        action=TransitionAction.REGRESS,
                        to_stage=prev_stage,
                        reason=f"Absence > 60 days: {days_since_last}",
                    )
                if state.trust_score < 0.30 and self._sustained_for_days(state, "low_trust", 30):
                    return StageDecision(
                        action=TransitionAction.REGRESS,
                        to_stage=prev_stage,
                        reason="Trust < 0.30 for 30+ days",
                    )

        elif current_stage == RelationshipStage.CONFIDANT:
            # To FRIEND from CONFIDANT
            if days_since_last > 30:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason=f"Absence > 30 days: {days_since_last}",
                )
            if state.conflict_debt > 0.6 and self._sustained_for_days(state, "high_conflict", 14):
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Unresolved conflict debt > 0.6 for 14+ days",
                )

        elif current_stage == RelationshipStage.ROMANTIC_INTEREST:
            # To CONFIDANT from ROMANTIC_INTEREST
            if days_since_last > 21:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason=f"Absence > 21 days: {days_since_last}",
                )

        elif current_stage == RelationshipStage.LOVER:
            # To ROMANTIC_INTEREST from LOVER
            if state.trust_score < 0.50 and self._sustained_for_days(state, "low_trust", 30):
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Trust < 0.50 for 30+ days",
                )
            if state.conflict_debt > 0.7:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Large unresolved conflict debt",
                )

        elif current_stage == RelationshipStage.BONDED:
            # To LOVER from BONDED (very rare)
            ritual_broken = self._check_ritual_broken(state, days=30)
            if ritual_broken and state.trust_score < 0.70:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Daily ritual broken > 30 days AND trust < 0.70",
                )

        return StageDecision(action=TransitionAction.STAY, reason="No regression conditions met")

    def _check_entry_requirements(
        self, state: RelationshipState, target_stage: RelationshipStage
    ) -> tuple[bool, str]:
        """
        Check hard entry requirements for target stage (§3.7).

        Returns:
            (satisfied, reason)
        """
        if target_stage == RelationshipStage.ACQUAINTANCE:
            if state.total_interactions < 5:
                return False, f"Need 5+ interactions, have {state.total_interactions}"
            if self._calculate_days_since_first(state) < 1:
                return False, "Need 1+ days since first meeting"
            if state.trust_score < 0.15:
                return False, f"Need trust >= 0.15, have {state.trust_score:.2f}"

        elif target_stage == RelationshipStage.FRIEND:
            if state.intimacy_level < 0.30:
                return False, f"Need intimacy >= 0.30, have {state.intimacy_level:.2f}"
            if state.trust_score < 0.40:
                return False, f"Need trust >= 0.40, have {state.trust_score:.2f}"
            if state.total_meaningful_disclosures < 5:
                return False, f"Need 5+ disclosures, have {state.total_meaningful_disclosures}"

        elif target_stage == RelationshipStage.CONFIDANT:
            if state.intimacy_level < 0.55:
                return False, f"Need intimacy >= 0.55, have {state.intimacy_level:.2f}"
            if state.trust_score < 0.65:
                return False, f"Need trust >= 0.65, have {state.trust_score:.2f}"
            if state.attachment_strength < 0.40:
                return False, f"Need attachment >= 0.40, have {state.attachment_strength:.2f}"

        elif target_stage == RelationshipStage.ROMANTIC_INTEREST:
            if state.intimacy_level < 0.70:
                return False, f"Need intimacy >= 0.70, have {state.intimacy_level:.2f}"
            if state.trust_score < 0.75:
                return False, f"Need trust >= 0.75, have {state.trust_score:.2f}"
            if state.attachment_strength < 0.60:
                return False, f"Need attachment >= 0.60, have {state.attachment_strength:.2f}"

        elif target_stage == RelationshipStage.LOVER:
            if state.intimacy_level < 0.85:
                return False, f"Need intimacy >= 0.85, have {state.intimacy_level:.2f}"
            if state.trust_score < 0.80:
                return False, f"Need trust >= 0.80, have {state.trust_score:.2f}"
            if state.attachment_strength < 0.75:
                return False, f"Need attachment >= 0.75, have {state.attachment_strength:.2f}"
            # Check for active cold war
            if any(s.get("state_type") == "COLD_WAR" for s in state.active_special_states):
                return False, "Cannot enter LOVER during COLD_WAR"

        elif target_stage == RelationshipStage.BONDED:
            if state.intimacy_level < 0.95:
                return False, f"Need intimacy >= 0.95, have {state.intimacy_level:.2f}"
            if state.trust_score < 0.90:
                return False, f"Need trust >= 0.90, have {state.trust_score:.2f}"
            if state.attachment_strength < 0.85:
                return False, f"Need attachment >= 0.85, have {state.attachment_strength:.2f}"
            if (
                state.total_promises_made == 0
                or state.total_promises_kept / state.total_promises_made < 0.8
            ):
                return False, "Need promise keeping ratio >= 80%"

        return True, "Requirements satisfied"

    def _check_soul_gate(
        self, state: RelationshipState, target_stage: RelationshipStage
    ) -> tuple[bool, str]:
        """
        Check Soul-specific gates (§3.7).

        Uses Soul.relational_template.intimacy_resistance and
        vulnerability_unlock_thresholds.

        Returns:
            (passes, reason)
        """
        days_since_first = self._calculate_days_since_first(state)

        # Apply intimacy resistance (§3.7 ACQUAINTANCE soul_gate)
        if target_stage == RelationshipStage.ACQUAINTANCE:
            required_elapsed = self.intimacy_resistance * 10 * 0.3  # Formula from §3.7
            if days_since_first < required_elapsed:
                return (
                    False,
                    f"Soul gate: need {required_elapsed:.1f} days, have {days_since_first}",
                )

        # Apply vulnerability unlock thresholds
        if target_stage == RelationshipStage.FRIEND:
            # Check first vulnerability threshold
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 0:
                threshold = self.vulnerability_thresholds[0].get("intimacy_level", 0.40)
                if state.intimacy_level < threshold:
                    return (
                        False,
                        f"Soul gate: need intimacy >= {threshold} for vulnerability unlock",
                    )

        elif target_stage == RelationshipStage.ROMANTIC_INTEREST:
            # Check second vulnerability threshold
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 1:
                threshold = self.vulnerability_thresholds[1].get("intimacy_level", 0.65)
                if state.intimacy_level < threshold:
                    return False, f"Soul gate: need intimacy >= {threshold}"
            # Additional check: days × intimacy_resistance
            min_days = self.intimacy_resistance * 30
            if days_since_first < min_days:
                return False, f"Soul gate: need {min_days:.0f} days since first meeting"

        elif target_stage == RelationshipStage.LOVER:
            # Check third vulnerability threshold
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 2:
                threshold = self.vulnerability_thresholds[2].get("intimacy_level", 0.85)
                if state.intimacy_level < threshold:
                    return False, f"Soul gate: need intimacy >= {threshold}"

        elif target_stage == RelationshipStage.BONDED:
            # Check fourth vulnerability threshold
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 3:
                threshold = self.vulnerability_thresholds[3].get("intimacy_level", 0.95)
                if state.intimacy_level < threshold:
                    return False, f"Soul gate: need intimacy >= {threshold}"

        return True, "Soul gate passed"

    def _check_minimum_time(
        self, state: RelationshipState, current_stage: RelationshipStage
    ) -> tuple[bool, str]:
        """
        Check minimum time in current stage (§3.7, §8.4).

        Returns:
            (satisfied, reason)
        """
        min_days = MIN_DAYS_IN_STAGE.get(current_stage, 0)
        if min_days == 0:
            return True, "No minimum time requirement"

        days_in_stage = self._calculate_days_in_stage(state)
        if days_in_stage < min_days:
            return False, f"Need {min_days} days in stage, have {days_in_stage:.1f}"

        return True, f"Minimum time satisfied: {days_in_stage:.1f} days"

    def _check_anti_gaming(
        self, state: RelationshipState, signals: SignalBatch
    ) -> tuple[bool, str]:
        """
        Check anti-gaming rules (§3.7, §8.3).

        Prevents:
        - Spam interactions (short messages)
        - Sudden bursts of activity
        - Repeated promise-making without keeping

        Returns:
            (passes, reason)
        """
        # Check promise keeping ratio
        if state.total_promises_made > 0:
            ratio = state.total_promises_kept / state.total_promises_made
            if ratio < 0.5:
                return False, f"Promise keeping ratio too low: {ratio:.1%}"

        # Check for spam signals in batch
        spam_count = sum(1 for s in signals.positive if s.type == "spam_detected")
        if spam_count > 0:
            return False, "Spam interactions detected"

        return True, "Anti-gaming checks passed"

    def _get_next_stage(self, current: RelationshipStage) -> Optional[RelationshipStage]:
        """Get next stage in progression order."""
        current_order = STAGE_ORDER[current]
        for stage, order in STAGE_ORDER.items():
            if order == current_order + 1:
                return stage
        return None

    def _get_previous_stage(self, current: RelationshipStage) -> Optional[RelationshipStage]:
        """Get previous stage in regression order."""
        current_order = STAGE_ORDER[current]
        if current_order == 0:
            return None
        for stage, order in STAGE_ORDER.items():
            if order == current_order - 1:
                return stage
        return None

    def _calculate_days_since_first(self, state: RelationshipState) -> float:
        """Calculate days since first meeting."""
        now = datetime.now(timezone.utc)
        delta = now - state.first_meeting_at.replace(tzinfo=timezone.utc)
        return delta.total_seconds() / 86400

    def _calculate_days_since_last(self, state: RelationshipState) -> float:
        """Calculate days since last interaction."""
        if not state.last_interaction_at:
            return 0.0
        now = datetime.now(timezone.utc)
        delta = now - state.last_interaction_at.replace(tzinfo=timezone.utc)
        return delta.total_seconds() / 86400

    def _calculate_days_in_stage(self, state: RelationshipState) -> float:
        """Calculate days in current stage."""
        now = datetime.now(timezone.utc)
        delta = now - state.stage_entered_at.replace(tzinfo=timezone.utc)
        return delta.total_seconds() / 86400

    def _sustained_for_days(self, state: RelationshipState, condition: str, days: int) -> bool:
        """
        Check if a condition has been sustained for N days.

        This is a simplified version - a real implementation would
        track condition history in stage_metadata.
        """
        # TODO: Implement proper condition tracking in stage_metadata
        return False

    def _check_ritual_broken(self, state: RelationshipState, days: int) -> bool:
        """Check if daily ritual has been broken for N days."""
        rituals = state.rituals
        daily_check_in = rituals.get("daily_check_in", {})
        streak = daily_check_in.get("streak_days", 0)
        return streak == 0  # Simplified check
