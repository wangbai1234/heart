"""
Safety adapter — bridges heart.safety.safety_agent to ss07_orchestration.

Dependency direction: ss07 → safety (correct), not safety → ss07.

Uses HeuristicSafetyClassifier (sync, Aho-Corasick backed) from
heart.safety.safety_agent. Maps SafetyClassificationLevel (5-tier,
YAML-driven) to the orchestrator's SafetyLevel enum.

Spec: runtime_specs/07_agent_orchestration.md §3.4.2
"""

from __future__ import annotations

from heart.safety.safety_agent import HeuristicSafetyClassifier
from heart.safety.safety_agent import SafetyClassification as InternalSafetyClassification
from heart.safety.safety_agent import SafetyClassificationLevel

from .orchestrator import SafetyClassification, SafetyLevel

# ---------------------------------------------------------------------------
# Level mapping table (semantically 1:1)
# ---------------------------------------------------------------------------

_LEVEL_MAP: dict[SafetyClassificationLevel, SafetyLevel] = {
    SafetyClassificationLevel.NONE: SafetyLevel.GREEN,
    SafetyClassificationLevel.LOW: SafetyLevel.YELLOW,
    SafetyClassificationLevel.MEDIUM: SafetyLevel.ORANGE,
    SafetyClassificationLevel.HIGH: SafetyLevel.RED,
    SafetyClassificationLevel.PURPLE_CARE_REQUIRED: SafetyLevel.PURPLE,
}


def _level_directives(level: SafetyClassificationLevel) -> dict:
    """Provide prompt_directives mirroring the old in-file SafetyAgent behaviour."""
    if level == SafetyClassificationLevel.PURPLE_CARE_REQUIRED:
        return {"additional_directive": "CARE_PROTOCOL"}
    if level == SafetyClassificationLevel.HIGH:  # mapped to RED
        return {"force_brevity": True}
    if level == SafetyClassificationLevel.MEDIUM:  # mapped to ORANGE
        return {"additional_directive": "用户情绪低落，请温和回应，避免说教"}
    return {}


def _map_action(internal_action: str) -> str:
    """Map recommended_action strings when they differ between the two layers."""
    # The internal classifier's _level_action and the orchestrator's
    # recommended_action use the same string set. Keeping this explicit
    # for auditability.
    return internal_action


class OrchestratorSafetyAdapter:
    """Thin adapter: HeuristicSafetyClassifier → orchestrator SafetyClassification.

    The adapter is sync because HeuristicSafetyClassifier.classify() is sync
    (Aho-Corasick automaton, no I/O). This matches the current orchestrator
    hot-path which calls self.safety_agent.classify() synchronously.
    """

    def __init__(self) -> None:
        self._classifier = HeuristicSafetyClassifier()

    def classify(self, message: str) -> SafetyClassification:
        """Classify a user message and return an orchestrator-compatible result.

        Returns:
            SafetyClassification with level mapped from the 5-tier
            SafetyClassificationLevel to the orchestrator's SafetyLevel.
        """
        internal: InternalSafetyClassification = self._classifier.classify(message)

        mapped_level = _LEVEL_MAP[internal.level]

        return SafetyClassification(
            level=mapped_level,
            confidence=internal.confidence,
            triggered_categories=list(internal.triggered_categories),
            reason=internal.reason,
            recommended_action=_map_action(internal.recommended_action),
            prompt_directives=_level_directives(internal.level),
            message_hash=internal.message_hash,
        )
