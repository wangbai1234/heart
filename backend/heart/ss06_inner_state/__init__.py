"""
Subsystem 06: Inner State + Behavior Runtime

Components:
  - ActivityGenerator: Soul-curated daily activity selection
  - ConcernsTracker: Lingering thoughts from memory + emotion
  - InnerStateComposer: Aggregates all components into InnerState
  - InnerStateBlockBuilder: Converts InnerState → SS05-compatible prompt block
  - InitiativeDecider: Rule engine for proactive message decisions (8 gates × 7 triggers)
  - AnniversaryTracker: Reads L4 identity memories, surfaces upcoming anniversaries
  - ProactiveMessageGenerator: Generates proactive messages via SS05 Composer + ModelRouter
  - ProactiveScheduler: Redis ZSET-backed scheduling + idempotent dispatch
  - ProactiveSender: Background worker that polls due items and dispatches them
"""

from heart.ss06_inner_state.activity_generator import (
    Activity,
    ActivityGenerator,
    DayType,
    TimeOfDay,
)
from heart.ss06_inner_state.anniversary_tracker import (
    AnniversaryCandidate,
    AnniversaryCategory,
    AnniversaryPattern,
    AnniversaryTracker,
    AnniversaryTrackResult,
    L4AnniversarySource,
)
from heart.ss06_inner_state.block_builder import (
    InnerStateBlock,
    InnerStateBlockBuilder,
)
from heart.ss06_inner_state.composer import (
    DailyRitualState,
    EnergyPoint,
    InnerState,
    InnerStateComposer,
    ProactiveState,
    RitualState,
    TodayMood,
    TodayState,
    compose_inner_state,
)
from heart.ss06_inner_state.concerns_tracker import (
    ConcernSource,
    ConcernsTracker,
    UnfinishedThought,
    UserConcern,
)
from heart.ss06_inner_state.initiative_decider import (
    TRIGGER_EVALUATORS,
    TRIGGER_PRIORITY,
    # Constants
    WELLBEING_OVERRIDE_MATRIX,
    BehavioralEnvelope,
    EmotionState,
    # Core
    InitiativeDecider,
    InitiativeDecision,
    InnerLoopContext,
    InnerStateSlice,
    RelationshipState,
    RiskLevel,
    SoulSpec,
    # Enums
    Stage,
    TriggerClass,
    TriggerType,
    WellbeingMode,
    # Data structures
    WellbeingState,
    apply_adaptive_rate,
    apply_rin_hard_cap,
    # Helpers
    compute_wellbeing_mode,
    gate_envelope_allows,
    gate_min_gap_satisfied,
    gate_no_cold_war,
    gate_quiet_hours,
    gate_quota_not_exhausted,
    gate_safety_allows,
    # Gate functions (composable predicates)
    gate_stage_above_stranger,
    gate_user_not_active,
    trigger_anniversary_anticipation,
    # Trigger functions (composable predicates)
    trigger_anniversary_due,
    trigger_care_check_pressing,
    trigger_check_in_gap,
    trigger_longing_threshold,
    trigger_ritual_due,
    trigger_soul_internal_spark,
)
from heart.ss06_inner_state.proactive_message import (
    CHARACTER_LIMITS,
    DIRECTIVE_TEMPLATES,
    LONGING_MODULATION,
    GenerateResult,
    ProactiveMessage,
    ProactiveMessageGenerator,
)
from heart.ss06_inner_state.ritual_manager import (
    SOUL_RITUAL_FLAVOR,
    RitualCheckResult,
    RitualCompleteResult,
    RitualEvent,
    RitualManager,
    RitualStreakState,
    RitualType,
    StreakMilestone,
)
from heart.ss06_inner_state.scheduler import (
    # Constants
    DEFAULT_JITTER_SECONDS,
    DISPATCH_LOCK_TTL,
    DispatchResult,
    # Data structures
    PendingInitiative,
    # Scheduler
    ProactiveScheduler,
    # Background worker
    ProactiveSender,
    ScheduleResult,
    # Factory
    create_initiative,
)

__all__ = [
    # Activity Generator
    "Activity",
    "ActivityGenerator",
    "DayType",
    "TimeOfDay",
    # Anniversary Tracker
    "AnniversaryTracker",
    "AnniversaryTrackResult",
    "AnniversaryCandidate",
    "AnniversaryCategory",
    "AnniversaryPattern",
    "L4AnniversarySource",
    # Concerns Tracker
    "ConcernSource",
    "ConcernsTracker",
    "UnfinishedThought",
    "UserConcern",
    # Inner State Composer
    "InnerState",
    "InnerStateComposer",
    "TodayMood",
    "TodayState",
    "EnergyPoint",
    "ProactiveState",
    "DailyRitualState",
    "RitualState",
    "compose_inner_state",
    # Inner State Block Builder
    "InnerStateBlock",
    "InnerStateBlockBuilder",
    # Initiative Decider — Core
    "InitiativeDecider",
    "InitiativeDecision",
    "InnerLoopContext",
    # Initiative Decider — Enums
    "Stage",
    "RiskLevel",
    "WellbeingMode",
    "TriggerType",
    "TriggerClass",
    # Initiative Decider — Data structures
    "WellbeingState",
    "BehavioralEnvelope",
    "RelationshipState",
    "EmotionState",
    "SoulSpec",
    "InnerStateSlice",
    # Initiative Decider — Gates
    "gate_stage_above_stranger",
    "gate_envelope_allows",
    "gate_quiet_hours",
    "gate_user_not_active",
    "gate_min_gap_satisfied",
    "gate_no_cold_war",
    "gate_quota_not_exhausted",
    "gate_safety_allows",
    # Initiative Decider — Triggers
    "trigger_anniversary_due",
    "trigger_care_check_pressing",
    "trigger_longing_threshold",
    "trigger_ritual_due",
    "trigger_anniversary_anticipation",
    "trigger_check_in_gap",
    "trigger_soul_internal_spark",
    # Initiative Decider — Helpers
    "compute_wellbeing_mode",
    "apply_adaptive_rate",
    "apply_rin_hard_cap",
    # Initiative Decider — Constants
    "WELLBEING_OVERRIDE_MATRIX",
    "TRIGGER_PRIORITY",
    "TRIGGER_EVALUATORS",
    # Proactive Message Generator
    "ProactiveMessage",
    "ProactiveMessageGenerator",
    "GenerateResult",
    "DIRECTIVE_TEMPLATES",
    "CHARACTER_LIMITS",
    "LONGING_MODULATION",
    # Proactive Scheduler — Data structures
    "PendingInitiative",
    "ScheduleResult",
    "DispatchResult",
    # Proactive Scheduler — Core
    "ProactiveScheduler",
    "ProactiveSender",
    "create_initiative",
    # Proactive Scheduler — Constants
    "DEFAULT_JITTER_SECONDS",
    "DISPATCH_LOCK_TTL",
    # Ritual Manager (§3.9)
    "RitualManager",
    "RitualStreakState",
    "RitualCheckResult",
    "RitualCompleteResult",
    "RitualType",
    "StreakMilestone",
    "RitualEvent",
    "SOUL_RITUAL_FLAVOR",
]
