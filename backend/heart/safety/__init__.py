"""Safety subsystem — content moderation, critic agent, heuristic safety classifier, LLM safety classifier, wellbeing monitor, PURPLE care path, and compliance."""

from heart.safety.care_path import (
    CarePathAuditEvent,
    CarePathEngine,
    CarePathResponse,
    CarePathTemplate,
    ResolvedTemplate,
    TemplateLoader,
    TriggerSource,
    get_care_path_engine,
    get_load_errors,
    get_template_count,
    validate_all_templates,
)
from heart.safety.content_policy import ContentPolicyResult, evaluate_content_policy
from heart.safety.critic_agent import (
    CriticAgent,
    CriticFailure,
    CriticInput,
    CriticOutput,
    build_drift_event,
)
from heart.safety.safety_agent import (
    ClassificationResult,
    LexiconLoader,
    SafetyAgent,
    SeverityLevel,
    WellbeingAccumulator,
    detect_locale,
)
from heart.safety.safety_llm import (
    SafetyLLMClassifier,
    SafetyLLMResult,
)
from heart.safety.wellbeing_monitor import (
    ActionLadder,
    ActionTier,
    HysteresisManager,
    InterventionStatus,
    RiskDimension,
    RiskLevel,
    RiskScorer,
    Thresholds,
    WellbeingAlert,
    WellbeingDirective,
    WellbeingMonitor,
    WellbeingSignal,
    WellbeingState,
    WindowAggregator,
)

__all__ = [
    # Care Path (PURPLE)
    "CarePathAuditEvent",
    "CarePathEngine",
    "CarePathResponse",
    "CarePathTemplate",
    "ResolvedTemplate",
    "TemplateLoader",
    "TriggerSource",
    "get_care_path_engine",
    "get_load_errors",
    "get_template_count",
    "validate_all_templates",
    # Critic
    "CriticAgent",
    "CriticFailure",
    "CriticInput",
    "CriticOutput",
    "build_drift_event",
    # Tier-aware content policy
    "ContentPolicyResult",
    "evaluate_content_policy",
    # Safety
    "ClassificationResult",
    "LexiconLoader",
    "SafetyAgent",
    "SeverityLevel",
    "WellbeingAccumulator",
    "detect_locale",
    # Safety LLM
    "SafetyLLMClassifier",
    "SafetyLLMResult",
    # Wellbeing Monitor
    "ActionLadder",
    "ActionTier",
    "HysteresisManager",
    "InterventionStatus",
    "RiskDimension",
    "RiskLevel",
    "RiskScorer",
    "Thresholds",
    "WellbeingAlert",
    "WellbeingDirective",
    "WellbeingMonitor",
    "WellbeingSignal",
    "WellbeingState",
    "WindowAggregator",
]
