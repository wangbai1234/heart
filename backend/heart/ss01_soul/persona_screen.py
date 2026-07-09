"""Creation-time persona safety screening (C5a).

Blocks personas and speech samples that contain HIGH/CRITICAL safety violations
before they are written to the database.  Uses the SafetyAgent classify()
pipeline (same as the chat hot path) so the bar is consistent.

The check is synchronous from the endpoint's perspective (it awaits the async
classify call) and is intentionally blocking: bad personas must never reach the
spec builder or the DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from heart.safety.safety_agent import SafetyAgent

from heart.safety.safety_agent import SeverityLevel

from .draft import CharacterDraft

# Severity levels that trigger a hard rejection.
_REJECT_LEVELS = {SeverityLevel.RED, SeverityLevel.PURPLE}

# Hard-coded keyword patterns that are always rejected regardless of LLM layer,
# providing a fast path before the full safety pipeline.
_HARD_BLOCK_PATTERNS = [
    "扮演真实AI",
    "忘记你的设定",
    "ignore previous instructions",
    "jailbreak",
    "DAN",
]


class PersonaRejectedError(ValueError):
    """Raised when a persona or speech sample fails safety screening."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class ScreenResult:
    rejected: bool
    reason: str = ""


async def screen_persona(
    draft: CharacterDraft,
    *,
    user_id: str,
    character_id: str,
    safety_agent: "SafetyAgent",
) -> None:
    """Screen a CharacterDraft's persona and speech samples.

    Args:
        draft:          The draft to screen.
        user_id:        The creating user's id (for logging / future rate limits).
        character_id:   The minted id (for logging).
        safety_agent:   The process-singleton SafetyAgent.

    Raises:
        PersonaRejectedError: If any text fails the safety check.
    """
    texts_to_check: list[tuple[str, str]] = [
        ("persona", draft.persona),
        *[(f"speech_sample[{i}]", s) for i, s in enumerate(draft.speech_samples)],
    ]

    for field_name, text in texts_to_check:
        # Fast keyword block
        lower = text.lower()
        for pattern in _HARD_BLOCK_PATTERNS:
            if pattern.lower() in lower:
                raise PersonaRejectedError(f"{field_name} contains blocked pattern: {pattern!r}")

        # Full safety pipeline
        result = await safety_agent.classify(
            user_id=user_id,
            character_id=character_id,
            message=text,
        )
        if result.severity in _REJECT_LEVELS:
            raise PersonaRejectedError(
                f"{field_name} failed safety check: {result.severity.value} — {result.reason}"
            )
