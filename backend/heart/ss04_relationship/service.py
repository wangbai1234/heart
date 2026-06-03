"""
SS04 Relationship Service — high-level facade for the Composer.

Wraps StagePhaseEngine per character_id (lazily instantiated),
manages per-(user, character) RelationshipState in memory (MVP),
and exposes get_current_phase() for the composer hot path.

Architecture:
    RelationshipService(soul_registry)
        ├── _engines: Dict[character_id, StagePhaseEngine]
        ├── _states: Dict[(user_id, character_id), RelationshipState]
        └── get_current_phase(user_id, character_id) -> dict
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

# phase → display name map
PHASE_DISPLAY: Dict[str, str] = {
    "STRANGER": "stranger",
    "ACQUAINTANCE": "acquaintance",
    "FRIEND": "friend",
    "CONFIDANT": "confidant",
    "ROMANTIC_INTEREST": "romantic_interest",
    "LOVER": "lover",
    "BONDED": "bonded",
}


class RelationshipService:
    """Per-(user, character) relationship state manager.

    Provides get_current_phase() for the Composer hot path.
    Internally caches RelationshipState and lazily builds
    StagePhaseEngine per character from SoulRegistry.

    Usage:
        svc = RelationshipService(soul_registry)
        phase = svc.get_current_phase(user_id, character_id)
    """

    def __init__(
        self,
        soul_registry=None,
        db_session=None,
    ):
        self._soul_registry = soul_registry
        self._db = db_session
        self._states: Dict[tuple, Any] = {}
        self._engines: Dict[str, Any] = {}

    def _key(self, user_id: UUID, character_id: str) -> tuple:
        return (str(user_id), character_id)

    def _get_engine(self, character_id: str):
        """Lazily build/return StagePhaseEngine for character."""
        if character_id not in self._engines:
            soul_spec = None
            if self._soul_registry is not None:
                try:
                    soul_spec_obj = self._soul_registry.get_soul(character_id)
                    inner = getattr(soul_spec_obj, "model_dump", None)
                    if inner is not None:
                        soul_spec = inner()
                    else:
                        soul_spec = getattr(soul_spec_obj, "__dict__", {})
                except Exception:
                    logger.warning(
                        "relationship_engine_soul_lookup_failed",
                        character_id=character_id,
                    )
            if soul_spec is None:
                soul_spec = {}
            from heart.ss04_relationship.stage_engine import StagePhaseEngine

            self._engines[character_id] = StagePhaseEngine(soul_spec)
        return self._engines[character_id]

    def _get_or_create_state(self, user_id: UUID, character_id: str):
        """Fetch or create default RelationshipState for the pair."""
        key = self._key(user_id, character_id)
        if key not in self._states:
            from heart.ss04_relationship.models import RelationshipState

            now = datetime.now(timezone.utc)
            self._states[key] = RelationshipState(
                user_id=user_id,
                character_id=character_id,
                first_meeting_at=now,
                stage_entered_at=now,
            )
            # ensure engine exists
            self._get_engine(character_id)
        return self._states[key]

    def get_current_phase(
        self,
        user_id: UUID,
        character_id: str,
    ) -> Dict[str, Any]:
        """Return current relationship phase dict for composer context.

        Returns:
            {
                "phase": str,             # "stranger" | "friend" | ...
                "trust_level": float,     # [0, 1]
                "attachment_style": str,  # e.g. "secure" | "anxious" | ""
                "behavioral_envelope": {}, # behavioural cues
            }
        """
        state = self._get_or_create_state(user_id, character_id)
        stage = getattr(state, "current_stage", "STRANGER") or "STRANGER"
        trust = float(getattr(state, "trust_score", 0.0) or 0.0)
        attachment = float(getattr(state, "attachment_strength", 0.0) or 0.0)

        attachment_style = ""
        if attachment > 0.7:
            attachment_style = "secure"
        elif attachment > 0.4:
            attachment_style = "anxious"

        # behavioural envelope: cues derived from stage + trust
        behavioural_envelope: Dict[str, Any] = {}
        if stage in ("FRIEND", "CONFIDANT"):
            behavioural_envelope["warmth_modifier"] = 0.3
        elif stage in ("ROMANTIC_INTEREST", "LOVER"):
            behavioural_envelope["warmth_modifier"] = 0.5
            behavioural_envelope["teasing_frequency"] = "high"

        return {
            "phase": PHASE_DISPLAY.get(stage, stage.lower()),
            "trust_level": trust,
            "attachment_style": attachment_style,
            "behavioral_envelope": behavioural_envelope,
        }

    def update_state(
        self,
        user_id: UUID,
        character_id: str,
        **kwargs,
    ) -> None:
        """Update the cached state fields (used by seed scripts, tests, etc.)."""
        state = self._get_or_create_state(user_id, character_id)
        for k, v in kwargs.items():
            if hasattr(state, k):
                setattr(state, k, v)
        state.updated_at = datetime.now(timezone.utc)
