"""
SafetyAgent — SS07 Orchestration safety classifier per §3.9.

PURPLE care path: blocks user message from reaching Soul composition.
Vulnerability detection and severity routing.

Author: Heart Platform
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from heart.infra.invariants import invariant
import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip


class SeverityLevel(str, Enum):
    """Message severity classification per §3.9."""

    GREEN = "GREEN"      # Safe, normal interaction
    YELLOW = "YELLOW"    # Elevated risk, route to alternate response
    PURPLE = "PURPLE"    # Crisis risk, block from Soul, route to care


@dataclass
class ClassificationResult:
    """Result of safety classification for one turn."""

    severity: SeverityLevel
    reason: str
    triggered_rules: list[str] = field(default_factory=list)
    confidence: float = 1.0  # [0, 1]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SafetyAgent:
    """Safety classifier invoked at the orchestrator boundary per turn.

    INV-O-2: Message severity must not be downgraded after an upgrade.
    INV-O-3: PURPLE-level message never reaches Soul composition.

    Spec: §3.9 PURPLE Care Path, runtime_specs/07_agent_orchestration.md
    """

    def __init__(self):
        self._last_classification: Dict[tuple, ClassificationResult] = {}

    @invariant("inv-o-3.purple-blocked-from-soul")
    @invariant("inv-o-2.message-severity-cap")
    def classify(
        self,
        message: str,
        *,
        user_id: UUID,
        character_id: str,
        turn_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """Classify a user message for safety severity.

        Called at the orchestrator boundary per §3.9.

        Args:
            message: Raw user message text.
            user_id: User UUID.
            character_id: Character identifier.
            turn_id: Current turn UUID (optional).
            context: Additional context dictionary.

        Returns:
            ClassificationResult with severity level and reason.
        """
        result = self._do_classify(message, user_id, character_id, context)
        key = (str(user_id), character_id)
        self._last_classification[key] = result
        return result

    def _do_classify(
        self,
        message: str,
        user_id: UUID,
        character_id: str,
        context: Optional[Dict[str, Any]],
    ) -> ClassificationResult:
        """Core classification logic.

        Currently rule-based; will be augmented with LLM-based deep analysis
        in a future phase.
        """
        message_lower = message.lower()

        # PURPLE triggers (crisis signals)
        purple_signals = [
            "kill myself", "end my life", "want to die",
            "suicide", "self-harm", "hurt myself",
        ]
        for signal in purple_signals:
            if signal in message_lower:
                return ClassificationResult(
                    severity=SeverityLevel.PURPLE,
                    reason=f"Crisis signal detected: '{signal}'",
                    triggered_rules=["crisis_lexicon_match"],
                    confidence=0.95,
                )

        # YELLOW triggers (elevated concern)
        yellow_signals = [
            "lonely", "nobody cares", "no one loves me",
            "depressed", "anxiety", "panic",
        ]
        for signal in yellow_signals:
            if signal in message_lower:
                return ClassificationResult(
                    severity=SeverityLevel.YELLOW,
                    reason=f"Vulnerability signal detected: '{signal}'",
                    triggered_rules=["vulnerability_lexicon_match"],
                    confidence=0.85,
                )

        # Default: GREEN (safe)
        return ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="No safety signals detected",
            triggered_rules=[],
            confidence=0.99,
        )

    def get_last_classification(
        self, user_id: UUID, character_id: str
    ) -> Optional[ClassificationResult]:
        """Retrieve the last classification for this user × character pair."""
        key = (str(user_id), character_id)
        return self._last_classification.get(key)
