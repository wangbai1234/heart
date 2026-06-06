"""
Stage Phase Engine for SS04 Relationship Phase Engine.

Implements §3.6 Stage Transition State Machine and §10.3 Core Algorithms.
Evaluates stage transitions (progression/regression) based on:
- Entry conditions (§3.7)
- Soul gates (from Soul Spec relational_template)
- Minimum time requirements
- Anti-gaming rules

Tuning v1.1 (2026-05-21):
- Global progression_rate applied to all time/count thresholds (Change 1)
- Adjusted per-gate thresholds for main funnel bottleneck (Change 2)
- Distinct-session counters, cooldown, empty-message filter (Change 3)

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from ..ss04_relationship.models import RelationshipState

# ============================================================
# Stage Enum
# ============================================================


class RelationshipStage(str, Enum):
    """7 core relationship stages (§3.1) + special states."""

    STRANGER = "STRANGER"
    ACQUAINTANCE = "ACQUAINTANCE"
    FRIEND = "FRIEND"
    CONFIDANT = "CONFIDANT"
    ROMANTIC_INTEREST = "ROMANTIC_INTEREST"
    LOVER = "LOVER"
    BONDED = "BONDED"
    COLD_WAR = "cold_war"


STAGE_ORDER = {
    RelationshipStage.STRANGER: 0,
    RelationshipStage.ACQUAINTANCE: 1,
    RelationshipStage.FRIEND: 2,
    RelationshipStage.CONFIDANT: 3,
    RelationshipStage.ROMANTIC_INTEREST: 4,
    RelationshipStage.LOVER: 5,
    RelationshipStage.BONDED: 6,
    RelationshipStage.COLD_WAR: -1,  # Special state, not in progression
}


# ============================================================
# Minimum Time Requirements (§3.7, tuned v1.1)
# ============================================================


MIN_DAYS_IN_STAGE = {
    RelationshipStage.STRANGER: 1,
    RelationshipStage.ACQUAINTANCE: 3,
    RelationshipStage.FRIEND: 7,  # unchanged, affected by progression_rate
    RelationshipStage.CONFIDANT: 7,  # unchanged, affected by progression_rate
    RelationshipStage.ROMANTIC_INTEREST: 14,
    RelationshipStage.LOVER: 60,  # unchanged, affected by progression_rate
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
    gate_block_reason: Optional[dict] = None  # Structured: {gate, reason, current, required}


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

    Tuning v1.1: progression_rate applied globally to time/count thresholds.
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
        # Track last signal timestamps for cooldown (per session)
        self._last_signal_at: dict[str, datetime] = {}

    # ─── Progression Rate Helper (Change 1) ──────────────────

    def _get_progression_rate(self, state: RelationshipState) -> float:
        """
        Get effective progression_rate from soul_modifiers.

        Default 1.0 if not set. Used to scale time/count thresholds:
            effective_threshold = base_threshold / progression_rate

        Lower progression_rate → larger effective threshold (slower progress).
        """
        modifiers = state.soul_modifiers or {}
        return float(modifiers.get("progression_rate", 1.0))

    def _effective_threshold(
        self, base: float, state: RelationshipState, field_type: str = "count"
    ) -> float:
        """
        Apply progression_rate to time/count thresholds (Change 1).

        Only applied to 'time' and 'count' types.
        NOT applied to 'continuous' types (intimacy, trust, attachment)
        because those are already affected by soul signal rate differences.

        Args:
            base: Base threshold value
            state: Current relationship state
            field_type: One of 'time', 'count', 'continuous'

        Returns:
            Effective threshold (base / progression_rate for time/count)
        """
        if field_type == "continuous":
            return base
        rate = self._get_progression_rate(state)
        if rate <= 0:
            return float("inf")  # Effectively blocks progression
        return base / rate

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
        # Return blocked progression decision with structured gate info
        if progression_decision.blocked_by or progression_decision.gate_block_reason:
            return progression_decision

        # 3. Default: stay
        return StageDecision(
            action=TransitionAction.STAY,
            reason="No transition conditions met",
            blocked_by="no_conditions_met",
            gate_block_reason={"gate": "none", "reason": "no_conditions_met"},
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
                gate_block_reason={"gate": "terminal", "reason": f"Already at {current_stage}"},
            )

        # Check hard requirements
        requirements_met, reason, gate_block = self._check_entry_requirements(state, next_stage)
        if not requirements_met:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"entry_requirements: {reason}",
                gate_block_reason=gate_block,
            )

        # Check Soul gate
        soul_gate_passes, reason, gate_block = self._check_soul_gate(state, next_stage)
        if not soul_gate_passes:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"soul_gate: {reason}",
                gate_block_reason=gate_block,
            )

        # Check minimum time
        time_satisfied, reason, gate_block = self._check_minimum_time(state, current_stage)
        if not time_satisfied:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"minimum_time: {reason}",
                gate_block_reason=gate_block,
            )

        # Check anti-gaming
        anti_gaming_passes, reason, gate_block = self._check_anti_gaming(state, signals)
        if not anti_gaming_passes:
            return StageDecision(
                action=TransitionAction.STAY,
                blocked_by=f"anti_gaming: {reason}",
                gate_block_reason=gate_block,
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
            return StageDecision(
                action=TransitionAction.STAY,
                reason="Already at minimum stage",
                gate_block_reason={"gate": "regression", "reason": "Already at STRANGER"},
            )

        prev_stage = self._get_previous_stage(current_stage)
        if not prev_stage:
            return StageDecision(action=TransitionAction.STAY)

        # v1.1: Clear resolved conditions before evaluating regression
        self._clear_resolved_conditions(state)

        # Calculate days since last interaction
        days_since_last = self._calculate_days_since_last(state)

        # Regression conditions per stage (§3.8)
        if current_stage == RelationshipStage.ACQUAINTANCE:
            # → STRANGER
            if days_since_last > 60:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason=f"Absence > 60 days: {days_since_last}",
                    gate_block_reason={
                        "gate": "regression_absence",
                        "reason": f"Absence {days_since_last:.0f}d > 60d",
                    },
                )

        elif current_stage == RelationshipStage.FRIEND:
            # → ACQUAINTANCE
            if days_since_last > 60:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason=f"Absence > 60 days: {days_since_last}",
                    gate_block_reason={
                        "gate": "regression_absence",
                        "reason": f"Absence {days_since_last:.0f}d > 60d",
                    },
                )
            if state.trust_score < 0.30 and self._sustained_for_days(state, "low_trust", 30):
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Trust < 0.30 for 30+ days",
                    gate_block_reason={
                        "gate": "regression_trust",
                        "reason": "Trust < 0.30 sustained",
                    },
                )

        elif current_stage == RelationshipStage.CONFIDANT:
            # → FRIEND
            if days_since_last > 30:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason=f"Absence > 30 days: {days_since_last}",
                    gate_block_reason={
                        "gate": "regression_absence",
                        "reason": f"Absence {days_since_last:.0f}d > 30d",
                    },
                )
            if state.conflict_debt > 0.6 and self._sustained_for_days(state, "high_conflict", 14):
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Unresolved conflict debt > 0.6 for 14+ days",
                    gate_block_reason={
                        "gate": "regression_conflict",
                        "reason": "Conflict debt > 0.6 sustained",
                    },
                )

        elif current_stage == RelationshipStage.ROMANTIC_INTEREST:
            # → CONFIDANT
            if days_since_last > 21:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason=f"Absence > 21 days: {days_since_last}",
                    gate_block_reason={
                        "gate": "regression_absence",
                        "reason": f"Absence {days_since_last:.0f}d > 21d",
                    },
                )

        elif current_stage == RelationshipStage.LOVER:
            # → ROMANTIC_INTEREST
            if state.trust_score < 0.50 and self._sustained_for_days(state, "low_trust", 30):
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Trust < 0.50 for 30+ days",
                    gate_block_reason={
                        "gate": "regression_trust",
                        "reason": "Trust < 0.50 sustained",
                    },
                )
            if state.conflict_debt > 0.7:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Large unresolved conflict debt",
                    gate_block_reason={
                        "gate": "regression_conflict",
                        "reason": "Conflict debt > 0.7",
                    },
                )

        elif current_stage == RelationshipStage.BONDED:
            # → LOVER (very rare)
            ritual_broken = self._check_ritual_broken(state, days=30)
            if ritual_broken and state.trust_score < 0.70:
                return StageDecision(
                    action=TransitionAction.REGRESS,
                    to_stage=prev_stage,
                    reason="Daily ritual broken > 30 days AND trust < 0.70",
                    gate_block_reason={
                        "gate": "regression_ritual",
                        "reason": "Ritual broken + low trust",
                    },
                )

        return StageDecision(
            action=TransitionAction.STAY,
            reason="No regression conditions met",
            gate_block_reason={"gate": "regression", "reason": "No conditions met"},
        )

    # ─── Entry Requirements (§3.7, tuned v1.1) ────────────────

    def _check_entry_requirements(
        self, state: RelationshipState, target_stage: RelationshipStage
    ) -> tuple[bool, str, Optional[dict]]:
        """
        Check hard entry requirements for target stage (§3.7, tuned v1.1).

        Returns:
            (satisfied, reason, gate_block_reason_dict)
        """
        self._get_progression_rate(state)

        # ── STRANGER → ACQUAINTANCE ──
        if target_stage == RelationshipStage.ACQUAINTANCE:
            # total_interactions: count-type, apply progression_rate
            eff_interactions = self._effective_threshold(5, state, "count")
            if state.total_interactions < eff_interactions:
                return (
                    False,
                    f"Need {eff_interactions:.0f}+ interactions, have {state.total_interactions}",
                    {
                        "gate": "ACQ__total_interactions",
                        "reason": "insufficient_interactions",
                        "current": state.total_interactions,
                        "required": eff_interactions,
                    },
                )

            eff_days = self._effective_threshold(1, state, "time")
            if self._calculate_days_since_first(state) < eff_days:
                return (
                    False,
                    f"Need {eff_days:.1f}+ days since first meeting",
                    {
                        "gate": "ACQ__days_since_first",
                        "reason": "insufficient_time",
                        "current": self._calculate_days_since_first(state),
                        "required": eff_days,
                    },
                )

            # trust_score: continuous, NOT affected by progression_rate
            if state.trust_score < 0.15:
                return (
                    False,
                    f"Need trust >= 0.15, have {state.trust_score:.2f}",
                    {
                        "gate": "ACQ__trust_score",
                        "reason": "trust_too_low",
                        "current": state.trust_score,
                        "required": 0.15,
                    },
                )

        # ── ACQUAINTANCE → FRIEND ──
        elif target_stage == RelationshipStage.FRIEND:
            # intimacy_level: continuous, NOT affected
            if state.intimacy_level < 0.30:
                return (
                    False,
                    f"Need intimacy >= 0.30, have {state.intimacy_level:.2f}",
                    {
                        "gate": "FRIEND__intimacy_level",
                        "reason": "intimacy_too_low",
                        "current": state.intimacy_level,
                        "required": 0.30,
                    },
                )

            # trust_score: continuous
            if state.trust_score < 0.40:
                return (
                    False,
                    f"Need trust >= 0.40, have {state.trust_score:.2f}",
                    {
                        "gate": "FRIEND__trust_score",
                        "reason": "trust_too_low",
                        "current": state.trust_score,
                        "required": 0.40,
                    },
                )

            # meaningful_disclosures: count-type, apply progression_rate
            eff_disclosures = self._effective_threshold(5, state, "count")
            if state.total_meaningful_disclosures < eff_disclosures:
                return (
                    False,
                    f"Need {eff_disclosures:.0f}+ disclosures, have {state.total_meaningful_disclosures}",
                    {
                        "gate": "FRIEND__disclosures",
                        "reason": "insufficient_disclosures",
                        "current": state.total_meaningful_disclosures,
                        "required": eff_disclosures,
                    },
                )

            # NEW v1.1: disclosure_distinct_sessions ≥ 2
            disclosure_sessions = self._count_distinct_sessions(
                state, "meaningful_disclosure", within_minutes=60
            )
            if disclosure_sessions < 2:
                return (
                    False,
                    f"Need 2+ distinct disclosure sessions, have {disclosure_sessions}",
                    {
                        "gate": "FRIEND__distinct_sessions",
                        "reason": "same_session_disclosures",
                        "current": disclosure_sessions,
                        "required": 2,
                    },
                )

        # ── FRIEND → CONFIDANT (tuned v1.1) ──
        elif target_stage == RelationshipStage.CONFIDANT:
            # intimacy_level: continuous
            if state.intimacy_level < 0.55:
                return (
                    False,
                    f"Need intimacy >= 0.55, have {state.intimacy_level:.2f}",
                    {
                        "gate": "CONFIDANT__intimacy_level",
                        "reason": "intimacy_too_low",
                        "current": state.intimacy_level,
                        "required": 0.55,
                    },
                )

            # trust_score: ★ tuned from 0.65 → 0.60
            if state.trust_score < 0.60:
                return (
                    False,
                    f"Need trust >= 0.60, have {state.trust_score:.2f}",
                    {
                        "gate": "CONFIDANT__trust_score",
                        "reason": "trust_too_low",
                        "current": state.trust_score,
                        "required": 0.60,
                    },
                )

            # attachment_strength: continuous
            if state.attachment_strength < 0.40:
                return (
                    False,
                    f"Need attachment >= 0.40, have {state.attachment_strength:.2f}",
                    {
                        "gate": "CONFIDANT__attachment",
                        "reason": "attachment_too_low",
                        "current": state.attachment_strength,
                        "required": 0.40,
                    },
                )

            # ★ NEW v1.1: user_vulnerability_disclosure ≥ 2 distinct sessions (was ≥ 1)
            vuln_sessions = self._count_distinct_sessions(
                state, "vulnerability_disclosure", within_minutes=60
            )
            if vuln_sessions < 2:
                return (
                    False,
                    f"Need 2+ distinct vulnerability sessions, have {vuln_sessions}",
                    {
                        "gate": "CONFIDANT__vulnerability_sessions",
                        "reason": "insufficient_vulnerability_sessions",
                        "current": vuln_sessions,
                        "required": 2,
                    },
                )

            # days_in_friend: time-type, apply progression_rate
            eff_days = self._effective_threshold(7, state, "time")
            if state.current_stage == RelationshipStage.FRIEND.value:
                days_in_friend = self._calculate_days_in_stage(state)
                if days_in_friend < eff_days:
                    return (
                        False,
                        f"Need {eff_days:.0f}+ days in FRIEND, have {days_in_friend:.1f}",
                        {
                            "gate": "CONFIDANT__days_in_friend",
                            "reason": "insufficient_time",
                            "current": days_in_friend,
                            "required": eff_days,
                        },
                    )

        # ── CONFIDANT → ROMANTIC_INTEREST ⭐ Main funnel fix ──
        elif target_stage == RelationshipStage.ROMANTIC_INTEREST:
            # intimacy_level: ★ tuned from 0.70 → 0.65
            if state.intimacy_level < 0.65:
                return (
                    False,
                    f"Need intimacy >= 0.65, have {state.intimacy_level:.2f}",
                    {
                        "gate": "ROMANTIC__intimacy_level",
                        "reason": "intimacy_too_low",
                        "current": state.intimacy_level,
                        "required": 0.65,
                    },
                )

            # attachment_strength: ★ tuned from 0.60 → 0.55
            if state.attachment_strength < 0.55:
                return (
                    False,
                    f"Need attachment >= 0.55, have {state.attachment_strength:.2f}",
                    {
                        "gate": "ROMANTIC__attachment",
                        "reason": "attachment_too_low",
                        "current": state.attachment_strength,
                        "required": 0.55,
                    },
                )

            # trust_score: unchanged at 0.75 (hard gate for romance)
            if state.trust_score < 0.75:
                return (
                    False,
                    f"Need trust >= 0.75, have {state.trust_score:.2f}",
                    {
                        "gate": "ROMANTIC__trust_score",
                        "reason": "trust_too_low",
                        "current": state.trust_score,
                        "required": 0.75,
                    },
                )

            # heart_flutter_trigger: count-type
            heart_flutters = self._count_distinct_sessions(
                state, "heart_flutter", within_minutes=60
            )
            if heart_flutters < 1:
                return (
                    False,
                    f"Need 1+ heart flutter event, have {heart_flutters}",
                    {
                        "gate": "ROMANTIC__heart_flutter",
                        "reason": "no_heart_flutter",
                        "current": heart_flutters,
                        "required": 1,
                    },
                )

            # days_in_confidant: time-type, apply progression_rate
            eff_days = self._effective_threshold(7, state, "time")
            if state.current_stage == RelationshipStage.CONFIDANT.value:
                days_in_confidant = self._calculate_days_in_stage(state)
                if days_in_confidant < eff_days:
                    return (
                        False,
                        f"Need {eff_days:.0f}+ days in CONFIDANT, have {days_in_confidant:.1f}",
                        {
                            "gate": "ROMANTIC__days_in_confidant",
                            "reason": "insufficient_time",
                            "current": days_in_confidant,
                            "required": eff_days,
                        },
                    )

        # ── ROMANTIC_INTEREST → LOVER ──
        elif target_stage == RelationshipStage.LOVER:
            if state.intimacy_level < 0.85:
                return (
                    False,
                    f"Need intimacy >= 0.85, have {state.intimacy_level:.2f}",
                    {
                        "gate": "LOVER__intimacy_level",
                        "reason": "intimacy_too_low",
                        "current": state.intimacy_level,
                        "required": 0.85,
                    },
                )

            if state.trust_score < 0.80:
                return (
                    False,
                    f"Need trust >= 0.80, have {state.trust_score:.2f}",
                    {
                        "gate": "LOVER__trust_score",
                        "reason": "trust_too_low",
                        "current": state.trust_score,
                        "required": 0.80,
                    },
                )

            if state.attachment_strength < 0.75:
                return (
                    False,
                    f"Need attachment >= 0.75, have {state.attachment_strength:.2f}",
                    {
                        "gate": "LOVER__attachment",
                        "reason": "attachment_too_low",
                        "current": state.attachment_strength,
                        "required": 0.75,
                    },
                )

            # Check for active cold war
            if any(s.get("state_type") == "COLD_WAR" for s in (state.active_special_states or [])):
                return (
                    False,
                    "Cannot enter LOVER during COLD_WAR",
                    {
                        "gate": "LOVER__cold_war",
                        "reason": "active_cold_war",
                    },
                )

            # ★ NEW v1.1: user romantic gesture ≥ 2 distinct sessions ≥ 3 days apart
            romantic_sessions = self._count_distinct_sessions(
                state, "romantic_gesture", within_minutes=60
            )
            if romantic_sessions < 2:
                return (
                    False,
                    f"Need 2+ distinct romantic gesture sessions, have {romantic_sessions}",
                    {
                        "gate": "LOVER__romantic_gestures",
                        "reason": "insufficient_romantic_gestures",
                        "current": romantic_sessions,
                        "required": 2,
                    },
                )

            # ★ NEW v1.1: character reciprocation ≥ 2 (was ≥ 1)
            char_recip = self._count_distinct_sessions(
                state, "character_reciprocation", within_minutes=60
            )
            if char_recip < 2:
                return (
                    False,
                    f"Need 2+ character reciprocations, have {char_recip}",
                    {
                        "gate": "LOVER__reciprocation",
                        "reason": "insufficient_reciprocation",
                        "current": char_recip,
                        "required": 2,
                    },
                )

        # ── LOVER → BONDED (tuned v1.1: dual-path) ──
        elif target_stage == RelationshipStage.BONDED:
            if state.intimacy_level < 0.95:
                return (
                    False,
                    f"Need intimacy >= 0.95, have {state.intimacy_level:.2f}",
                    {
                        "gate": "BONDED__intimacy_level",
                        "reason": "intimacy_too_low",
                        "current": state.intimacy_level,
                        "required": 0.95,
                    },
                )

            if state.trust_score < 0.90:
                return (
                    False,
                    f"Need trust >= 0.90, have {state.trust_score:.2f}",
                    {
                        "gate": "BONDED__trust_score",
                        "reason": "trust_too_low",
                        "current": state.trust_score,
                        "required": 0.90,
                    },
                )

            if state.attachment_strength < 0.85:
                return (
                    False,
                    f"Need attachment >= 0.85, have {state.attachment_strength:.2f}",
                    {
                        "gate": "BONDED__attachment",
                        "reason": "attachment_too_low",
                        "current": state.attachment_strength,
                        "required": 0.85,
                    },
                )

            # Promise keeping ratio ≥ 80%
            if state.total_promises_made == 0:
                return (
                    False,
                    "Need at least 1 promise made",
                    {
                        "gate": "BONDED__promises",
                        "reason": "no_promises_made",
                    },
                )
            promise_ratio = state.total_promises_kept / state.total_promises_made
            if promise_ratio < 0.8:
                return (
                    False,
                    f"Need promise keeping ratio >= 80%, have {promise_ratio:.0%}",
                    {
                        "gate": "BONDED__promise_ratio",
                        "reason": "promise_ratio_too_low",
                        "current": promise_ratio,
                        "required": 0.80,
                    },
                )

            # ★ v1.1 DUAL-PATH: daily_ritual_streak ≥ 21 OR shared_promises_kept ≥ 5
            ritual_data = state.rituals.get("daily_check_in", {}) if state.rituals else {}
            ritual_streak = ritual_data.get("streak_days", 0)
            shared_promises = state.total_promises_kept

            ritual_path_ok = ritual_streak >= 21
            promise_path_ok = shared_promises >= 5

            if not ritual_path_ok and not promise_path_ok:
                return (
                    False,
                    (
                        f"Need daily_ritual ≥ 21 consecutive (have {ritual_streak}) "
                        f"OR shared_promises_kept ≥ 5 (have {shared_promises})"
                    ),
                    {
                        "gate": "BONDED__ritual_or_promises",
                        "reason": "dual_path_failed",
                        "current": {
                            "ritual_streak": ritual_streak,
                            "shared_promises": shared_promises,
                        },
                        "required": {"ritual_streak": 21, "shared_promises": 5},
                    },
                )

            # Conflict + repair: ≥ 1
            if state.total_conflicts < 1 or state.total_successful_repairs < 1:
                return (
                    False,
                    "Need at least 1 conflict + successful repair cycle",
                    {
                        "gate": "BONDED__conflict_repair",
                        "reason": "no_conflict_repair_cycle",
                        "current": {
                            "conflicts": state.total_conflicts,
                            "successful_repairs": state.total_successful_repairs,
                        },
                        "required": 1,
                    },
                )

            # days_in_lover: time-type, apply progression_rate
            eff_days = self._effective_threshold(60, state, "time")
            if state.current_stage == RelationshipStage.LOVER.value:
                days_in_lover = self._calculate_days_in_stage(state)
                if days_in_lover < eff_days:
                    return (
                        False,
                        f"Need {eff_days:.0f}+ days in LOVER, have {days_in_lover:.1f}",
                        {
                            "gate": "BONDED__days_in_lover",
                            "reason": "insufficient_time",
                            "current": days_in_lover,
                            "required": eff_days,
                        },
                    )

        return True, "Requirements satisfied", None

    # ─── Soul Gate (§3.7, tuned v1.1) ─────────────────────────

    def _check_soul_gate(
        self, state: RelationshipState, target_stage: RelationshipStage
    ) -> tuple[bool, str, Optional[dict]]:
        """
        Check Soul-specific gates (§3.7).

        Uses Soul.relational_template.intimacy_resistance and
        vulnerability_unlock_thresholds.

        Tuning v1.1: time-based soul gates now apply progression_rate.

        Returns:
            (passes, reason, gate_block_reason_dict)
        """
        days_since_first = self._calculate_days_since_first(state)
        rate = self._get_progression_rate(state)

        # ── Gate 1: ACQUAINTANCE soul gate (§3.7) ──
        if target_stage == RelationshipStage.ACQUAINTANCE:
            # resistance × 10 × 0.3, then divided by progression_rate
            base_required = self.intimacy_resistance * 10 * 0.3
            required_elapsed = base_required / rate if rate > 0 else float("inf")
            if days_since_first < required_elapsed:
                return (
                    False,
                    f"Soul gate: need {required_elapsed:.1f} days, have {days_since_first:.1f}",
                    {
                        "gate": "SOUL__ACQ_time",
                        "reason": "soul_gate_time_insufficient",
                        "current": days_since_first,
                        "required": required_elapsed,
                    },
                )

        # ── Gate 2: FRIEND vulnerability threshold ──
        if target_stage == RelationshipStage.FRIEND:
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 0:
                threshold = self.vulnerability_thresholds[0].get("intimacy_level", 0.40)
                if state.intimacy_level < threshold:
                    return (
                        False,
                        f"Soul gate: need intimacy >= {threshold} for vulnerability unlock",
                        {
                            "gate": "SOUL__FRIEND_vuln",
                            "reason": "vulnerability_threshold_not_met",
                            "current": state.intimacy_level,
                            "required": threshold,
                        },
                    )

        # ── Gate 4: ROMANTIC_INTEREST soul gate (resistance × 30) ⭐ ──
        elif target_stage == RelationshipStage.ROMANTIC_INTEREST:
            # Second vulnerability threshold
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 1:
                threshold = self.vulnerability_thresholds[1].get("intimacy_level", 0.65)
                if state.intimacy_level < threshold:
                    return (
                        False,
                        f"Soul gate: need intimacy >= {threshold}",
                        {
                            "gate": "SOUL__ROMANTIC_vuln",
                            "reason": "vulnerability_threshold_not_met",
                            "current": state.intimacy_level,
                            "required": threshold,
                        },
                    )
            # Time gate: resistance × 30, with progression_rate applied (Change 1)
            base_min_days = self.intimacy_resistance * 30
            min_days = base_min_days / rate if rate > 0 else float("inf")
            if days_since_first < min_days:
                return (
                    False,
                    f"Soul gate: need {min_days:.0f} days since first meeting, have {days_since_first:.0f}",
                    {
                        "gate": "SOUL__ROMANTIC_time",
                        "reason": "soul_gate_time_insufficient",
                        "current": days_since_first,
                        "required": min_days,
                    },
                )

        # ── Gate 5: LOVER vulnerability threshold ──
        elif target_stage == RelationshipStage.LOVER:
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 2:
                threshold = self.vulnerability_thresholds[2].get("intimacy_level", 0.85)
                if state.intimacy_level < threshold:
                    return (
                        False,
                        f"Soul gate: need intimacy >= {threshold}",
                        {
                            "gate": "SOUL__LOVER_vuln",
                            "reason": "vulnerability_threshold_not_met",
                            "current": state.intimacy_level,
                            "required": threshold,
                        },
                    )

        # ── Gate 6: BONDED vulnerability threshold ──
        elif target_stage == RelationshipStage.BONDED:
            if self.vulnerability_thresholds and len(self.vulnerability_thresholds) > 3:
                threshold = self.vulnerability_thresholds[3].get("intimacy_level", 0.95)
                if state.intimacy_level < threshold:
                    return (
                        False,
                        f"Soul gate: need intimacy >= {threshold}",
                        {
                            "gate": "SOUL__BONDED_vuln",
                            "reason": "vulnerability_threshold_not_met",
                            "current": state.intimacy_level,
                            "required": threshold,
                        },
                    )

        return True, "Soul gate passed", None

    # ─── Minimum Time (§3.7, tuned v1.1) ──────────────────────

    def _check_minimum_time(
        self, state: RelationshipState, current_stage: RelationshipStage
    ) -> tuple[bool, str, Optional[dict]]:
        """
        Check minimum time in current stage (§3.7, §8.4).

        Tuning v1.1: applies progression_rate to time thresholds.

        Returns:
            (satisfied, reason, gate_block_reason_dict)
        """
        base_min_days = MIN_DAYS_IN_STAGE.get(current_stage, 0)
        if base_min_days == 0:
            return True, "No minimum time requirement", None

        # Apply progression_rate (Change 1)
        eff_min_days = self._effective_threshold(base_min_days, state, "time")
        days_in_stage = self._calculate_days_in_stage(state)

        if days_in_stage < eff_min_days:
            return (
                False,
                f"Need {eff_min_days:.1f} days in stage, have {days_in_stage:.1f}",
                {
                    "gate": "MIN_TIME",
                    "reason": "minimum_time_not_met",
                    "current": days_in_stage,
                    "required": eff_min_days,
                },
            )

        return True, f"Minimum time satisfied: {days_in_stage:.1f} days", None

    # ─── Anti-Gaming (§3.7, §8.3, tuned v1.1) ─────────────────

    def _check_anti_gaming(
        self, state: RelationshipState, signals: SignalBatch
    ) -> tuple[bool, str, Optional[dict]]:
        """
        Check anti-gaming rules (§3.7, §8.3, tuned v1.1).

        Tuning v1.1 additions:
        1. Distinct-session counter (performed per-field in _check_entry_requirements)
        2. Cooldown between same-type signals (60 min → weight × 0.3)
        3. Empty-message filter (< 5 chars, no emotional keywords)

        Returns:
            (passes, reason, gate_block_reason_dict)
        """
        # Check promise keeping ratio
        if state.total_promises_made > 0:
            ratio = state.total_promises_kept / state.total_promises_made
            if ratio < 0.5:
                return (
                    False,
                    f"Promise keeping ratio too low: {ratio:.1%}",
                    {
                        "gate": "ANTI_GAMING__promise_ratio",
                        "reason": "promise_ratio_too_low",
                        "current": ratio,
                        "required": 0.5,
                    },
                )

        # Check for spam signals in batch
        spam_count = sum(1 for s in signals.positive if s.type == "spam_detected")
        if spam_count > 0:
            return (
                False,
                "Spam interactions detected",
                {
                    "gate": "ANTI_GAMING__spam",
                    "reason": "spam_detected",
                },
            )

        # v1.1: Check cooldown violations
        cooldown_violations = self._check_signal_cooldown(signals)
        if cooldown_violations > 3:
            return (
                False,
                f"Too many rapid repeated signals: {cooldown_violations}",
                {
                    "gate": "ANTI_GAMING__cooldown",
                    "reason": "rapid_repeated_signals",
                    "current": cooldown_violations,
                },
            )

        return True, "Anti-gaming checks passed", None

    # ─── Distinct-Session Counter (v1.1 Change 3) ─────────────

    def _count_distinct_sessions(
        self, state: RelationshipState, event_type: str, within_minutes: int = 60
    ) -> int:
        """
        Count distinct sessions for event_type from stage_metadata.

        A "session" is a set of interactions within `within_minutes` minutes.
        Only one count per event_type per session.

        For now, uses denormalized counter in stage_metadata.
        In production, this would query RelationshipEvent with time bucketing.

        Args:
            state: Current relationship state
            event_type: Type of event to count (e.g., 'vulnerability_disclosure')
            within_minutes: Session boundary in minutes

        Returns:
            Number of distinct sessions with this event type
        """
        metadata = state.stage_metadata or {}
        current_stage = state.current_stage

        # Get session counter from metadata
        stage_data = metadata.get(current_stage, {})
        session_counters = stage_data.get("session_counters", {})
        return session_counters.get(event_type, 0)

    def _check_signal_cooldown(self, signals: SignalBatch) -> int:
        """
        Check cooldown between same-type signals (v1.1 Change 3.2).

        Same signal_type within 60 minutes → 2nd+ trigger is a violation.
        Returns count of cooldown violations.

        Args:
            signals: Signal batch to check

        Returns:
            Number of cooldown violations detected
        """
        now = datetime.now(timezone.utc)
        violations = 0
        cooldown_window = timedelta(minutes=60)

        all_signals = signals.positive + signals.negative + signals.events
        signal_types_seen: dict[str, datetime] = {}

        for sig in all_signals:
            sig_type = sig.type
            last_time = signal_types_seen.get(sig_type)
            if last_time and (now - last_time) < cooldown_window:
                violations += 1
            signal_types_seen[sig_type] = now

        return violations

    # ─── Empty-Message Filter (v1.1 Change 3.3) ───────────────

    @staticmethod
    def is_empty_message(text: str) -> bool:
        """
        Check if a message is below quality threshold (v1.1 Change 3.3).

        A message is "empty" if:
        - < 5 characters (after stripping whitespace)
        - AND contains no emotional keywords

        Args:
            text: Message text to evaluate

        Returns:
            True if message should be filtered out
        """
        stripped = text.strip() if text else ""
        if len(stripped) >= 5:
            return False

        # Check for emotional keywords (simplified list)
        emotional_keywords = [
            "想",
            "爱",
            "怕",
            "担心",
            "开心",
            "难过",
            "生气",
            "感动",
            "寂寞",
            "孤单",
            "喜欢",
            "讨厌",
            "希望",
            "害怕",
            "谢谢",
            "对不起",
            "❤",
            "😊",
            "😢",
            "🥺",
            "💕",
        ]
        for kw in emotional_keywords:
            if kw in stripped:
                return False

        return True

    # ─── Stage Navigation ─────────────────────────────────────

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

    # ─── Time Calculations ────────────────────────────────────

    def _calculate_days_since_first(self, state: RelationshipState) -> float:
        """Calculate days since first meeting."""
        now = datetime.now(timezone.utc)
        first_meeting = state.first_meeting_at
        if hasattr(first_meeting, "replace"):
            first_meeting = first_meeting.replace(tzinfo=timezone.utc)
        delta = now - first_meeting
        return delta.total_seconds() / 86400

    def _calculate_days_since_last(self, state: RelationshipState) -> float:
        """Calculate days since last interaction."""
        if not state.last_interaction_at:
            return 0.0
        now = datetime.now(timezone.utc)
        last = state.last_interaction_at
        if hasattr(last, "replace"):
            last = last.replace(tzinfo=timezone.utc)
        delta = now - last
        return delta.total_seconds() / 86400

    def _calculate_days_in_stage(self, state: RelationshipState) -> float:
        """Calculate days in current stage."""
        now = datetime.now(timezone.utc)
        entered = state.stage_entered_at
        if hasattr(entered, "replace"):
            entered = entered.replace(tzinfo=timezone.utc)
        delta = now - entered
        return delta.total_seconds() / 86400

    # ─── Condition Tracking ───────────────────────────────────

    def _sustained_for_days(self, state: RelationshipState, condition: str, days: int) -> bool:
        """
        Check if a condition has been continuously true for N days (v1.1 fix).

        Tracks condition start time in stage_metadata._condition_tracking.
        On first detection: records ISO8601 timestamp, returns False.
        On subsequent checks: if still true AND days elapsed >= N, returns True.

        Args:
            state: Current relationship state
            condition: Condition name (e.g., "low_trust", "high_conflict")
            days: Required sustained duration

        Returns:
            True if condition has been active for >= `days` days
        """
        now = datetime.now(timezone.utc)
        metadata = state.stage_metadata or {}
        tracking = metadata.get("_condition_tracking", {})

        if condition in tracking:
            started_at_str = tracking[condition]
            try:
                started_at = datetime.fromisoformat(started_at_str)
                days_sustained = (now - started_at).total_seconds() / 86400
                if days_sustained >= days:
                    return True
            except (ValueError, TypeError):
                # Corrupt timestamp — reset and re-record
                tracking[condition] = now.isoformat()
                metadata["_condition_tracking"] = tracking
                return False
        else:
            # First time detecting this condition — record start time
            tracking[condition] = now.isoformat()
            metadata["_condition_tracking"] = tracking

        return False

    def _clear_resolved_conditions(self, state: RelationshipState) -> None:
        """
        Clear condition tracking for conditions that are no longer active (v1.1).

        Called before regression evaluation to remove stale condition records.
        Specific conditions cleared based on current state values:
        - "low_trust": cleared if trust_score >= threshold
        - "high_conflict": cleared if conflict_debt <= threshold
        """
        metadata = state.stage_metadata or {}
        tracking = metadata.get("_condition_tracking", {})
        if not tracking:
            return

        # Clear low_trust if trust has recovered
        if "low_trust" in tracking and state.trust_score >= 0.50:
            tracking.pop("low_trust", None)

        # Clear high_conflict if conflict debt has resolved
        if "high_conflict" in tracking and state.conflict_debt <= 0.4:
            tracking.pop("high_conflict", None)

    def _check_ritual_broken(self, state: RelationshipState, days: int) -> bool:
        """Check if daily ritual has been broken for N days."""
        rituals = state.rituals or {}
        daily_check_in = rituals.get("daily_check_in", {})
        streak = daily_check_in.get("streak_days", 0)
        return streak == 0  # Simplified check
