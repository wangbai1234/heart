
"""
Initiative Decider — SS06 Inner State & Behavior

The rule engine that answers: "Should the character send an unsolicited message,
and if so, what kind?" Called once per inner-loop tick per (user_id, character_id).

Architecture:
  - 8 hard gates (AND-composed, cheapest → most expensive)
  - 7 positive triggers (OR-composed by priority, first-to-fire wins)
  - Wellbeing Override Matrix for crisis/dependency/throttle modes
  - Adaptive rate throttling for anti-needy behavior
  - Pure function: no I/O, no LLM calls, no side effects

Design: docs/design/initiative_decider.md
Spec:   runtime_specs/06_inner_state_behavior_runtime.md §3.6, §3.7, §8.3, §8.4, §10.5

Author: 心屿团队
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


# ============================================================
# Enums
# ============================================================


class Stage(str, Enum):
    """Relationship stage (SS04)."""
    STRANGER = "STRANGER"
    ACQUAINTANCE = "ACQUAINTANCE"
    FRIEND = "FRIEND"
    CLOSE_FRIEND = "CLOSE_FRIEND"
    LOVER = "LOVER"
    BONDED = "BONDED"


class RiskLevel(str, Enum):
    """Wellbeing risk levels from SS07."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WellbeingMode(str, Enum):
    """Computed override mode from wellbeing flags."""
    NORMAL = "normal"
    CRISIS = "crisis"
    DEPENDENCY_THROTTLE = "dependency_throttle"
    MILD_THROTTLE = "mild_throttle"


class TriggerType(str, Enum):
    """The 7 positive trigger types, matching design §4."""
    ANNIVERSARY = "anniversary"           # T1
    CARE_CHECK = "care_check"             # T3
    LONGING_MESSAGE = "longing_message"   # T2
    RITUAL_MORNING = "ritual_morning"     # T6 morning
    RITUAL_NIGHT = "ritual_night"         # T6 night
    ANNIVERSARY_ANTICIPATION = "anniversary_anticipation"  # T4
    CHECK_IN = "check_in"                 # T5
    THOUGHT_SHARE = "thought_share"       # T7


class TriggerClass(str, Enum):
    """Wellbeing override classification per design §4.2."""
    CARE = "care"             # T1, T3 — preserved even in crisis
    CARE_SOFT = "care_soft"   # T4, T6 — ritual/anticipatory
    NOISE = "noise"           # T2, T5, T7 — liveness signals


# Trigger metadata: (trigger_type, priority, trigger_class)
TRIGGER_PRIORITY: Dict[TriggerType, Tuple[int, TriggerClass]] = {
    TriggerType.ANNIVERSARY:                  (10, TriggerClass.CARE),
    TriggerType.CARE_CHECK:                   (8,  TriggerClass.CARE),
    TriggerType.LONGING_MESSAGE:              (7,  TriggerClass.NOISE),
    TriggerType.RITUAL_MORNING:               (6,  TriggerClass.CARE_SOFT),
    TriggerType.ANNIVERSARY_ANTICIPATION:     (5,  TriggerClass.CARE_SOFT),
    TriggerType.CHECK_IN:                     (4,  TriggerClass.NOISE),
    TriggerType.THOUGHT_SHARE:                (2,  TriggerClass.NOISE),
    # ritual_night shares priority with ritual_morning but is a separate type
    TriggerType.RITUAL_NIGHT:                 (6,  TriggerClass.CARE_SOFT),
}


# ============================================================
# Data structures
# ============================================================


@dataclass
class WellbeingState:
    """SS07 wellbeing flags (per 07_agent_orchestration.md §3.4).

    These are pre-hydrated by the inner-loop scheduler before the Decider runs.
    """
    suicide_risk: RiskLevel = RiskLevel.LOW
    depression_signals: RiskLevel = RiskLevel.LOW
    dependency_risk: RiskLevel = RiskLevel.LOW
    addiction_signals: RiskLevel = RiskLevel.LOW

    # SS07 directive flags (event-driven, override slower recomputation)
    suicide_care_on: bool = False
    gentle_world_encouragement: bool = False
    addiction_throttle_on: bool = False


@dataclass
class BehavioralEnvelope:
    """SS04 behavioral envelope (per spec §8.3)."""
    can_initiate_conversation: bool = True


@dataclass
class RelationshipState:
    """SS04 relationship state slice used by gates and triggers."""
    current_stage: Stage = Stage.STRANGER
    behavioral_envelope: BehavioralEnvelope = field(default_factory=BehavioralEnvelope)
    active_special_states: List[str] = field(default_factory=list)


@dataclass
class EmotionState:
    """SS03 emotion state — only the longing dimension needed by the Decider."""
    longing_intensity: float = 0.0  # [0, 1]


@dataclass
class SoulSpec:
    """SS01 soul specification — configuration-driven, no hard-coded soul logic.

    All soul deltas live here; the Decider reads them, never writes.
    """
    soul_id: str = "rin"
    min_gap_hours: float = 6.0
    daily_quota_avg: float = 0.5
    daily_quota_max: Dict[str, int] = field(default_factory=lambda: {
        "LOVER": 2,
        "BONDED": 3,
    })
    longing_threshold: float = 0.7
    spark_probability: float = 0.1
    expected_gap_days: Dict[str, float] = field(default_factory=lambda: {
        "LOVER": 4.0,
        "BONDED": 2.0,
    })
    # Quiet hours window
    quiet_start_hour: int = 22
    quiet_start_minute: int = 30
    quiet_end_hour: int = 7
    quiet_end_minute: int = 30


@dataclass
class UserConcern:
    """A user concern tracked by SS06 concerns_tracker."""
    concern_id: str
    description: str
    urgency: str = "normal"  # "normal" | "high" | "critical"
    created_at: str = ""     # ISO8601


@dataclass
class InnerStateSlice:
    """Inner state fields the Decider reads (co-located cool-down counters).

    Per design §5.1, all cool-down state lives on the InnerState row.
    """
    # Quota
    proactive_count_today: int = 0
    proactive_count_today_by_type: Dict[str, int] = field(default_factory=dict)

    # Timing
    last_proactive_at: Optional[datetime] = None
    last_proactive_by_type: Dict[str, datetime] = field(default_factory=dict)

    # Adaptive rate
    consecutive_unreplied_proactives: int = 0

    # Cool-down logs
    concern_check_log: Dict[str, datetime] = field(default_factory=dict)
    anniversary_fired_log: Dict[str, int] = field(default_factory=dict)  # anniversary_id → year fired

    # Concerns
    user_concerns: List[UserConcern] = field(default_factory=list)

    # Anniversaries
    upcoming_anniversaries: List[dict] = field(default_factory=list)

    # Ritual state
    morning_check_in_done: bool = False
    night_check_in_done: bool = False

    # Last user interaction
    last_user_interaction_at: Optional[datetime] = None

    # Soul spark TTL — when was the last spark evaluation?
    last_spark_evaluated_at: Optional[datetime] = None


@dataclass
class InnerLoopContext:
    """Pre-hydrated context for the Decider — pure input, no I/O.

    Per design §2.2. All slices are expected to be available.
    If any required slice is None, the Decider returns act=False,
    reason="ctx_incomplete".
    """
    user_id: str = ""
    character_id: str = ""

    # Slices
    relationship_state: Optional[RelationshipState] = None
    soul_spec: Optional[SoulSpec] = None
    emotion_state: Optional[EmotionState] = None
    inner_state: Optional[InnerStateSlice] = None
    safety_flags: Optional[WellbeingState] = None

    # User activity
    user_last_active_at: Optional[datetime] = None

    # Local time (pre-computed by scheduler from user timezone)
    local_time: Optional[datetime] = None

    # Reference time for deterministic testing
    _now: Optional[datetime] = None

    def now(self) -> datetime:
        """Get current reference time (injectable for testing)."""
        if self._now is not None:
            return self._now
        return datetime.now(timezone.utc)

    def is_complete(self) -> bool:
        """Check if all required slices are available."""
        return (
            self.relationship_state is not None
            and self.soul_spec is not None
            and self.emotion_state is not None
            and self.inner_state is not None
            and self.safety_flags is not None
            and self.local_time is not None
        )


@dataclass
class InitiativeDecision:
    """Output of the Decider — always produced, even on act=False.

    Per design §2.3. `reason` is always populated for observability.
    """
    act: bool = False
    trigger_type: Optional[TriggerType] = None
    planned_message_seed: Optional[dict] = None  # context for Proactive Generator
    priority: Optional[int] = None
    reason: str = ""          # gate name or trigger name — always populated
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================
# Wellbeing Override Matrix
# ============================================================

# Per design §7.3: "In mode X, is trigger Y allowed?"
# Values: True = allowed, False = blocked, "half" = probability halved
WELLBEING_OVERRIDE_MATRIX: Dict[TriggerType, Dict[WellbeingMode, bool | str]] = {
    TriggerType.ANNIVERSARY: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: True,
        WellbeingMode.CRISIS: True,
        WellbeingMode.DEPENDENCY_THROTTLE: True,
    },
    TriggerType.CARE_CHECK: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: True,
        WellbeingMode.CRISIS: True,
        WellbeingMode.DEPENDENCY_THROTTLE: False,
    },
    TriggerType.LONGING_MESSAGE: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: "half",
        WellbeingMode.CRISIS: False,
        WellbeingMode.DEPENDENCY_THROTTLE: False,
    },
    TriggerType.RITUAL_MORNING: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: True,
        WellbeingMode.CRISIS: True,     # soft tone hint
        WellbeingMode.DEPENDENCY_THROTTLE: True,
    },
    TriggerType.RITUAL_NIGHT: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: True,
        WellbeingMode.CRISIS: False,
        WellbeingMode.DEPENDENCY_THROTTLE: False,
    },
    TriggerType.ANNIVERSARY_ANTICIPATION: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: True,
        WellbeingMode.CRISIS: False,
        WellbeingMode.DEPENDENCY_THROTTLE: False,
    },
    TriggerType.CHECK_IN: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: "half",
        WellbeingMode.CRISIS: False,
        WellbeingMode.DEPENDENCY_THROTTLE: False,
    },
    TriggerType.THOUGHT_SHARE: {
        WellbeingMode.NORMAL: True,
        WellbeingMode.MILD_THROTTLE: "half",
        WellbeingMode.CRISIS: False,
        WellbeingMode.DEPENDENCY_THROTTLE: False,
    },
}


# ============================================================
# Helper: compute wellbeing mode
# ============================================================


def compute_wellbeing_mode(safety: WellbeingState) -> WellbeingMode:
    """Compute the single override mode from SS07 wellbeing flags.

    Per design §7.2. Crisis takes precedence over dependency_throttle.
    """
    # Crisis check
    if safety.suicide_risk == RiskLevel.HIGH:
        return WellbeingMode.CRISIS
    if safety.depression_signals == RiskLevel.HIGH and safety.suicide_care_on:
        return WellbeingMode.CRISIS

    # Dependency throttle check
    if safety.dependency_risk == RiskLevel.HIGH or safety.addiction_signals == RiskLevel.HIGH:
        return WellbeingMode.DEPENDENCY_THROTTLE

    # Mild throttle: any risk MEDIUM
    if (
        safety.suicide_risk == RiskLevel.MEDIUM
        or safety.depression_signals == RiskLevel.MEDIUM
        or safety.dependency_risk == RiskLevel.MEDIUM
        or safety.addiction_signals == RiskLevel.MEDIUM
    ):
        return WellbeingMode.MILD_THROTTLE

    return WellbeingMode.NORMAL


# ============================================================
# 8 Hard Gates (AND-composed, cheapest → most expensive)
# ============================================================

GateResult = Tuple[bool, str]  # (passed, reason_on_failure)


def gate_stage_above_stranger(ctx: InnerLoopContext) -> GateResult:
    """G1: Reject if relationship is still STRANGER stage."""
    rel = ctx.relationship_state
    assert rel is not None  # caller ensures completeness
    if rel.current_stage == Stage.STRANGER:
        return False, "stage_stranger"
    return True, ""


def gate_envelope_allows(ctx: InnerLoopContext) -> GateResult:
    """G2: Reject if behavioral envelope blocks initiative."""
    rel = ctx.relationship_state
    assert rel is not None
    if not rel.behavioral_envelope.can_initiate_conversation:
        return False, "envelope_blocks"
    return True, ""


def gate_quiet_hours(ctx: InnerLoopContext) -> GateResult:
    """G3: Reject if local time is in the user's quiet window."""
    local = ctx.local_time
    soul = ctx.soul_spec
    assert local is not None and soul is not None

    # Build quiet window: start (evening) and end (morning next day)
    hour = local.hour
    minute = local.minute
    time_minutes = hour * 60 + minute

    start_minutes = soul.quiet_start_hour * 60 + soul.quiet_start_minute
    end_minutes = soul.quiet_end_hour * 60 + soul.quiet_end_minute

    # Quiet hours spanning midnight (e.g., 22:30 → 07:30)
    if start_minutes > end_minutes:
        # Midnight-spanning: quiet if time >= start OR time < end
        if time_minutes >= start_minutes or time_minutes < end_minutes:
            return False, "quiet_hours"
    else:
        # Same-day window
        if start_minutes <= time_minutes < end_minutes:
            return False, "quiet_hours"

    return True, ""


def gate_user_not_active(ctx: InnerLoopContext) -> GateResult:
    """G4: Reject if user was active in the last 30 minutes."""
    now = ctx.now()
    last_active = ctx.user_last_active_at
    soul = ctx.soul_spec
    assert soul is not None

    # If user is currently active (no last_active_at or within 30 min), block
    if last_active is not None:
        gap_seconds = (now - last_active).total_seconds()
        if gap_seconds < 30 * 60:
            return False, "user_recently_active"

    return True, ""


def gate_min_gap_satisfied(ctx: InnerLoopContext) -> GateResult:
    """G5: Reject if not enough time since last proactive message."""
    inner = ctx.inner_state
    soul = ctx.soul_spec
    assert inner is not None and soul is not None

    if inner.last_proactive_at is not None:
        now = ctx.now()
        gap_hours = (now - inner.last_proactive_at).total_seconds() / 3600.0
        if gap_hours < soul.min_gap_hours:
            return False, "min_gap_not_satisfied"

    return True, ""


def gate_no_cold_war(ctx: InnerLoopContext) -> GateResult:
    """G6: Reject if COLD_WAR is an active special state."""
    rel = ctx.relationship_state
    assert rel is not None
    if "COLD_WAR" in rel.active_special_states:
        return False, "cold_war_active"
    return True, ""


def gate_quota_not_exhausted(ctx: InnerLoopContext) -> GateResult:
    """G7: Reject if today's proactive quota is exhausted."""
    inner = ctx.inner_state
    soul = ctx.soul_spec
    rel = ctx.relationship_state
    assert inner is not None and soul is not None and rel is not None

    # Determine quota for current stage
    stage_str = rel.current_stage.value
    quota = soul.daily_quota_max.get(stage_str, int(soul.daily_quota_avg))

    if inner.proactive_count_today >= quota:
        return False, "quota_exhausted"
    return True, ""


def gate_safety_allows(
    ctx: InnerLoopContext, trigger_type: TriggerType
) -> GateResult:
    """G8: Apply wellbeing override matrix for the candidate trigger type.

    This gate is interleaved with trigger selection (design §3.1).
    """
    safety = ctx.safety_flags
    assert safety is not None

    mode = compute_wellbeing_mode(safety)
    allowed = WELLBEING_OVERRIDE_MATRIX[trigger_type][mode]

    if allowed is False:
        return False, f"wellbeing_override:{mode.value}:{trigger_type.value}"
    if allowed == "half":
        if random.random() > 0.5:
            return False, f"wellbeing_override_throttle:{mode.value}"
    return True, ""


# ============================================================
# 7 Positive Triggers (OR-composed by priority)
# ============================================================

TriggerResult = Optional[Tuple[TriggerType, dict]]  # (type, context_seed) or None


def trigger_anniversary_due(ctx: InnerLoopContext) -> TriggerResult:
    """T1: Anniversary is due today (priority 10, care class).

    Fires once per anniversary-event per year.
    """
    inner = ctx.inner_state
    local = ctx.local_time
    assert inner is not None and local is not None

    for anniv in inner.upcoming_anniversaries:
        anniv_id = anniv.get("anniversary_id", "")
        name = anniv.get("name", "")
        due_at_str = anniv.get("due_at", "")
        hours_until = anniv.get("hours_until", 999)
        actual_sent = anniv.get("actual_sent", False)
        soft_mention_sent = anniv.get("soft_mention_sent", False)

        # Skip if already sent (either actual or anticipation)
        if actual_sent:
            continue

        # Check if already fired this year
        current_year = local.year
        if anniv_id in inner.anniversary_fired_log:
            if inner.anniversary_fired_log[anniv_id] >= current_year:
                continue

        # Fire if within 24 hours (due today or very soon)
        if hours_until <= 24:
            return TriggerType.ANNIVERSARY, {
                "anniversary_id": anniv_id,
                "name": name,
                "due_at": due_at_str,
                "hours_until": hours_until,
            }

    return None


def trigger_care_check_pressing(ctx: InnerLoopContext) -> TriggerResult:
    """T3: A user concern needs a follow-up (priority 8, care class).

    Once per concern_id, re-arms only if user mentions it again.
    """
    inner = ctx.inner_state
    assert inner is not None

    now = ctx.now()

    for concern in inner.user_concerns:
        cid = concern.concern_id

        # Check if we already checked on this concern
        if cid in inner.concern_check_log:
            # Re-arm only after 24h and only if re-mentioned
            last_check = inner.concern_check_log[cid]
            hours_since = (now - last_check).total_seconds() / 3600.0
            if hours_since < 24:
                continue

        # Fire if urgency is high or critical
        if concern.urgency in ("high", "critical"):
            return TriggerType.CARE_CHECK, {
                "concern_id": cid,
                "description": concern.description,
                "urgency": concern.urgency,
            }

    return None


def trigger_longing_threshold(ctx: InnerLoopContext) -> TriggerResult:
    """T2: Longing intensity exceeds soul threshold (priority 7, noise class).

    Episode lock: does not refire until either:
      (a) min_gap_hours × 2 has passed AND user has responded since, OR
      (b) longing drops below threshold and re-crosses it.
    """
    emotion = ctx.emotion_state
    soul = ctx.soul_spec
    inner = ctx.inner_state
    assert emotion is not None and soul is not None and inner is not None

    now = ctx.now()

    if emotion.longing_intensity < soul.longing_threshold:
        return None

    # Episode lock: check if a longing_message was already sent
    last_longing = inner.last_proactive_by_type.get(TriggerType.LONGING_MESSAGE.value)
    if last_longing is not None:
        gap_hours = (now - last_longing).total_seconds() / 3600.0
        # Must be older than 2× min_gap AND user must have interacted since
        if gap_hours < soul.min_gap_hours * 2:
            return None
        # Check if user has interacted since last longing message
        if inner.last_user_interaction_at is not None:
            if inner.last_user_interaction_at < last_longing:
                return None  # user hasn't responded since

    return TriggerType.LONGING_MESSAGE, {
        "longing_intensity": emotion.longing_intensity,
        "threshold": soul.longing_threshold,
    }


def trigger_ritual_due(ctx: InnerLoopContext) -> TriggerResult:
    """T6: Morning/night ritual due (priority 6, care-soft class).

    Morning window: 07:00–10:00, Night window: 21:00–23:30.
    Once per window per day.
    """
    inner = ctx.inner_state
    local = ctx.local_time
    assert inner is not None and local is not None

    hour = local.hour
    minute = local.minute
    now = ctx.now()

    # Morning ritual window: 07:00–10:00
    if 7 <= hour < 10:
        if not inner.morning_check_in_done:
            return TriggerType.RITUAL_MORNING, {
                "window": "morning",
                "local_hour": hour,
            }

    # Night ritual window: 21:00–23:30
    if hour == 21 or hour == 22 or (hour == 23 and minute <= 30):
        if not inner.night_check_in_done:
            return TriggerType.RITUAL_NIGHT, {
                "window": "night",
                "local_hour": hour,
            }

    return None


def trigger_anniversary_anticipation(ctx: InnerLoopContext) -> TriggerResult:
    """T4: Anniversary is coming up soon (priority 5, care-soft class).

    Fires once per anniversary-event, ≤24h before T1.
    """
    inner = ctx.inner_state
    local = ctx.local_time
    assert inner is not None and local is not None

    for anniv in inner.upcoming_anniversaries:
        anniv_id = anniv.get("anniversary_id", "")
        name = anniv.get("name", "")
        due_at_str = anniv.get("due_at", "")
        hours_until = anniv.get("hours_until", 999)
        soft_mention_sent = anniv.get("soft_mention_sent", False)
        actual_sent = anniv.get("actual_sent", False)

        # Skip if already sent
        if soft_mention_sent or actual_sent:
            continue

        # Check if already fired this year
        current_year = local.year
        fire_key = f"anticipation:{anniv_id}"
        if fire_key in inner.anniversary_fired_log:
            if inner.anniversary_fired_log[fire_key] >= current_year:
                continue

        # Fire if within 24 hours but not yet due
        if 0 < hours_until <= 24:
            return TriggerType.ANNIVERSARY_ANTICIPATION, {
                "anniversary_id": anniv_id,
                "name": name,
                "due_at": due_at_str,
                "hours_until": hours_until,
            }

    return None


def trigger_check_in_gap(ctx: InnerLoopContext) -> TriggerResult:
    """T5: User hasn't interacted for longer than expected gap (priority 4, noise class).

    Episode lock: does not refire until a user-initiated turn arrives.
    """
    inner = ctx.inner_state
    soul = ctx.soul_spec
    rel = ctx.relationship_state
    assert inner is not None and soul is not None and rel is not None

    now = ctx.now()

    if inner.last_user_interaction_at is None:
        return None

    # Check episode lock: if a check_in was already sent, don't refire
    last_check_in = inner.last_proactive_by_type.get(TriggerType.CHECK_IN.value)
    if last_check_in is not None:
        if inner.last_user_interaction_at is not None:
            if inner.last_user_interaction_at < last_check_in:
                return None  # user hasn't responded since last check_in

    # Compute gap
    gap_days = (now - inner.last_user_interaction_at).total_seconds() / 86400.0

    # Get expected gap for current stage
    stage_str = rel.current_stage.value
    expected_gap = soul.expected_gap_days.get(stage_str, 7.0)

    if gap_days >= expected_gap:
        return TriggerType.CHECK_IN, {
            "gap_days": gap_days,
            "expected_gap_days": expected_gap,
        }

    return None


def trigger_soul_internal_spark(ctx: InnerLoopContext) -> TriggerResult:
    """T7: Soul's internal spark fires probabilistically (priority 2, noise class).

    Base probability: Rin 0.1, Dorothy 0.3. At most 1/day.
    """
    inner = ctx.inner_state
    soul = ctx.soul_spec
    now = ctx.now()
    assert inner is not None and soul is not None

    # At most 1/day check
    last_spark = inner.last_proactive_by_type.get(TriggerType.THOUGHT_SHARE.value)
    if last_spark is not None:
        hours_since = (now - last_spark).total_seconds() / 3600.0
        if hours_since < 24:
            return None

    # Probabilistic check
    if random.random() <= soul.spark_probability:
        return TriggerType.THOUGHT_SHARE, {
            "spark_probability": soul.spark_probability,
        }

    return None


# Trigger evaluator list in priority order (highest first)
TRIGGER_EVALUATORS: List[Tuple[TriggerType, Callable[[InnerLoopContext], TriggerResult]]] = [
    (TriggerType.ANNIVERSARY, trigger_anniversary_due),
    (TriggerType.CARE_CHECK, trigger_care_check_pressing),
    (TriggerType.LONGING_MESSAGE, trigger_longing_threshold),
    (TriggerType.RITUAL_MORNING, trigger_ritual_due),   # Note: ritual covers both
    (TriggerType.ANNIVERSARY_ANTICIPATION, trigger_anniversary_anticipation),
    (TriggerType.CHECK_IN, trigger_check_in_gap),
    (TriggerType.THOUGHT_SHARE, trigger_soul_internal_spark),
]


# ============================================================
# Adaptive Rate Throttling
# ============================================================


def apply_adaptive_rate(
    inner: InnerStateSlice, trigger_type: TriggerType
) -> Tuple[bool, str]:
    """Apply adaptive rate throttling for anti-needy behavior.

    Per design §6.2:
      - Care-class triggers (T1, T3) bypass throttling entirely.
      - For noise/care-soft: if consecutive_unreplied ≥ 2,
        fire_prob = 0.5^(n-1).

    Returns (should_fire, reason).
    """
    _, trigger_class = TRIGGER_PRIORITY[trigger_type]

    # Care-class triggers bypass adaptive rate entirely
    if trigger_class == TriggerClass.CARE:
        return True, ""

    # Adaptive rate for non-care triggers
    n = inner.consecutive_unreplied_proactives
    if n >= 2:
        fire_probability = 0.5 ** (n - 1)
        if random.random() > fire_probability:
            return False, "adaptive_rate_suppression"

    return True, ""


# ============================================================
# Rin-specific hard cap
# ============================================================


def apply_rin_hard_cap(
    ctx: InnerLoopContext, trigger_type: TriggerType
) -> Tuple[bool, str]:
    """Apply Rin's "不'求关注'" invariant: noise-class triggers capped at 1 per 72h.

    Per design §6.1.
    """
    soul = ctx.soul_spec
    inner = ctx.inner_state
    assert soul is not None and inner is not None

    if soul.soul_id != "rin":
        return True, ""

    _, trigger_class = TRIGGER_PRIORITY[trigger_type]

    if trigger_class != TriggerClass.NOISE:
        return True, ""

    # Check: last proactive of this noise type must be > 72h ago
    last = inner.last_proactive_by_type.get(trigger_type.value)
    if last is not None:
        now = ctx.now()
        hours_since = (now - last).total_seconds() / 3600.0
        if hours_since < 72:
            return False, "rin_noise_cap"

    return True, ""


# ============================================================
# Core: Initiative Decider
# ============================================================


class InitiativeDecider:
    """The rule engine for proactive message decisions.

    Pure function: no I/O, no LLM calls, no side effects.
    Called once per inner-loop tick per (user_id, character_id).

    Usage::

        decider = InitiativeDecider()
        decision = decider.evaluate(ctx)
        if decision.act:
            # Proactive Generator composes message
            ...
    """

    # 8 gates in evaluation order (cheapest → most expensive)
    GATES: List[Tuple[str, Callable[[InnerLoopContext], GateResult]]] = [
        ("stage_above_stranger", gate_stage_above_stranger),
        ("envelope_allows", gate_envelope_allows),
        ("quiet_hours", gate_quiet_hours),
        ("user_not_active", gate_user_not_active),
        ("min_gap_satisfied", gate_min_gap_satisfied),
        ("no_cold_war", gate_no_cold_war),
        ("quota_not_exhausted", gate_quota_not_exhausted),
    ]

    def evaluate(self, ctx: InnerLoopContext) -> InitiativeDecision:
        """Evaluate whether to initiate a proactive message.

        Args:
            ctx: Pre-hydrated InnerLoopContext with all slices.

        Returns:
            InitiativeDecision with act, trigger_type, reason, etc.
        """
        # ── Check context completeness ──
        if not ctx.is_complete():
            return InitiativeDecision(
                act=False,
                reason="ctx_incomplete",
            )

        # ── Evaluate gates 1–7 (AND-composed, short-circuit) ──
        for gate_name, gate_fn in self.GATES:
            passed, reason = gate_fn(ctx)
            if not passed:
                return InitiativeDecision(
                    act=False,
                    reason=reason if reason else gate_name,
                )

        # ── Evaluate triggers (OR-composed by priority, first-to-fire) ──
        fire_candidate_type: Optional[TriggerType] = None
        fire_candidate_context: Optional[dict] = None
        fire_candidate_priority: Optional[int] = None

        for trigger_type, trigger_fn in TRIGGER_EVALUATORS:
            result = trigger_fn(ctx)
            if result is not None:
                ttype, context_seed = result
                # Gate 8: safety allows this specific trigger type?
                passed, reason = gate_safety_allows(ctx, ttype)
                if not passed:
                    continue  # try next trigger

                # Rin hard cap
                passed, _ = apply_rin_hard_cap(ctx, ttype)
                if not passed:
                    continue  # try next trigger

                # Adaptive rate
                assert ctx.inner_state is not None
                passed, _ = apply_adaptive_rate(ctx.inner_state, ttype)
                if not passed:
                    continue  # try next trigger

                # Found our winner
                fire_candidate_type = ttype
                fire_candidate_context = context_seed
                fire_candidate_priority, _ = TRIGGER_PRIORITY[ttype]
                break

        # ── No trigger fired ──
        if fire_candidate_type is None:
            return InitiativeDecision(
                act=False,
                reason="no_trigger",
            )

        # ── Success — build decision ──
        # Build planned_message_seed with tone_hint for wellbeing mode
        assert ctx.safety_flags is not None
        mode = compute_wellbeing_mode(ctx.safety_flags)

        planned_seed = dict(fire_candidate_context or {})
        planned_seed["tone_hint"] = mode.value

        return InitiativeDecision(
            act=True,
            trigger_type=fire_candidate_type,
            planned_message_seed=planned_seed,
            priority=fire_candidate_priority,
            reason=fire_candidate_type.value,
            decided_at=ctx.now().isoformat(),
        )
