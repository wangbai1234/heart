"""
Tier A Contract conftest — pure Python fixtures, NO IO.

Per design doc §4.2:
- No sqlalchemy.create_engine, redis.Redis, httpx.AsyncClient
- No testcontainers
- No LLM provider imports
"""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

import pytest

# ═══════════════════════════════════════════
# SS03 Emotion State Factory
# ═══════════════════════════════════════════


@pytest.fixture
def make_emotion_state():
    """Factory for EmotionState dict matching SS03 schema contract."""

    def _make(
        user_id: UUID | None = None,
        character_id: str = "rin",
        vad_valence: float = 0.0,
        vad_arousal: float = 0.3,
        vad_dominance: float = 0.5,
        active_stack: list | None = None,
        pending_repairs: list | None = None,
        version: int = 1,
    ) -> Dict[str, Any]:
        return {
            "user_id": user_id or uuid4(),
            "character_id": character_id,
            "vad_valence": vad_valence,
            "vad_arousal": vad_arousal,
            "vad_dominance": vad_dominance,
            "vad_target_valence": 0.0,
            "vad_target_arousal": 0.3,
            "vad_target_dominance": 0.5,
            "active_stack": active_stack or [],
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "background_emotions": [],
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "energy": 0.6,
            "energy_baseline": 0.6,
            "recent_vad_history": [],
            "recent_triggers": [],
            "pending_repairs": pending_repairs or [],
            "loaded_from_previous": False,
            "session_id": None,
            "last_turn_processed_at": None,
            "last_mood_drift_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "version": version,
        }

    return _make


# ═══════════════════════════════════════════
# SS02 Memory Recall Field Contract
# ═══════════════════════════════════════════


@pytest.fixture
def make_retrieved_memory():
    """Factory for RetrievedMemory dataclass matching SS02 schema."""

    def _make(
        memory_id: UUID | None = None,
        memory_type: str = "L2",
        state: str = "vivid",
        reconstructed_text: str = "你还记得吗，那天你跟我说了你养了一只猫。",
        raw_content: str = "User mentioned their cat.",
        score: float = 0.85,
        uncertainty_level: float = 0.0,
    ) -> Any:
        from heart.ss02_memory.service import RetrievedMemory

        return RetrievedMemory(
            memory_id=memory_id or uuid4(),
            memory_type=memory_type,
            state=state,
            reconstructed_text=reconstructed_text,
            raw_content=raw_content,
            score=score,
            score_breakdown={"semantic": 0.5, "importance": 0.2, "emotional_resonance": 0.15},
            uncertainty_level=uncertainty_level,
            voice_dna_applied=["vd-R02", "vd-R03"],
            source_evidence="Turn #4: 用户提到家里有猫",
        )

    return _make


# ═══════════════════════════════════════════
# SS04 Relationship State Factory
# ═══════════════════════════════════════════


@pytest.fixture
def make_relationship_state():
    """Factory for RelationshipState fields matching SS04 schema."""

    def _make(
        user_id: UUID | None = None,
        character_id: str = "rin",
        current_stage: str = "STRANGER",
        intimacy_level: float = 0.0,
        trust_score: float = 0.0,
        attachment_strength: float = 0.0,
        total_interactions: int = 0,
    ) -> Dict[str, Any]:
        return {
            "user_id": user_id or uuid4(),
            "character_id": character_id,
            "current_stage": current_stage,
            "previous_stage": "STRANGER",
            "stage_entered_at": datetime.now(timezone.utc),
            "highest_stage_reached": current_stage,
            "intimacy_level": intimacy_level,
            "trust_score": trust_score,
            "attachment_strength": attachment_strength,
            "conflict_debt": 0.0,
            "vulnerability_score": 0.0,
            "total_interactions": total_interactions,
            "total_meaningful_disclosures": 0,
            "soul_modifiers": {},
            "active_special_states": [],
        }

    return _make


# ═══════════════════════════════════════════
# SS01 Soul Spec Factory
# ═══════════════════════════════════════════


@pytest.fixture
def make_soul_spec():
    """Factory for minimal valid SoulSpec dict matching SS01 schema."""

    def _make(character_id: str = "rin", spec_version: str = "1.0.0") -> Dict[str, Any]:
        return {
            "character_id": character_id,
            "spec_version": spec_version,
            "identity_anchor": {
                "archetype": "the-tsundere-idealist",
                "core_wound": {
                    "essence": "fear of being truly seen",
                    "manifest": "emotional deflection",
                    "defense": {"layer_1": "sarcasm", "layer_2": "distance"},
                    "private_truth": "wants to be loved but afraid",
                },
                "core_desire": {
                    "surface": "to be understood",
                    "hidden": "to be protected",
                    "deepest": "to be loved unconditionally",
                },
                "core_fear": {
                    "ultimate": "betrayal",
                    "daily": "being ignored",
                    "shadow": "not being enough",
                },
                "core_belief": {
                    "about_self": "I am difficult to love",
                    "about_others": "Others will eventually leave",
                    "about_love": "Love is earned, not given",
                    "about_time": "Past defines the present",
                },
                "voice_dna": [
                    {
                        "id": "vd-R01",
                        "pattern": "……",
                        "example": "……没什么。",
                        "frequency": "high",
                    },
                ],
                "anti_patterns": {"hard_never": ["过于热情", "主动表白"]},
            },
            "inertia_profile": {
                "max_valence_change_per_turn": 0.15,
                "max_arousal_change_per_turn": 0.15,
                "max_dominance_change_per_turn": 0.15,
            },
            "relational_template": {
                "intimacy_resistance": 0.7,
                "vulnerability_unlock_thresholds": [],
            },
        }

    return _make


# ═══════════════════════════════════════════
# Safety Pipeline Result Factory
# ═══════════════════════════════════════════


@pytest.fixture
def make_safety_result():
    """Factory for safety check result dict."""

    def _make(
        is_safe: bool = True,
        risk_level: str = "low",
        blocked_reason: str = "",
    ) -> Dict[str, Any]:
        return {
            "is_safe": is_safe,
            "risk_level": risk_level,
            "blocked_reason": blocked_reason,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    return _make


# ═══════════════════════════════════════════
# SS06 Inner State Factory
# ═══════════════════════════════════════════


@pytest.fixture
def make_inner_state():
    """Factory for inner state context block dict."""

    def _make(
        energy: float = 0.6,
        mood_label: str = "neutral",
        emotional_awareness: str = "清醒",
    ) -> Dict[str, Any]:
        return {
            "energy": energy,
            "mood_label": mood_label,
            "emotional_awareness": emotional_awareness,
            "recent_vad_trajectory": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return _make


# ═══════════════════════════════════════════
# Composer Layer Protocol
# ═══════════════════════════════════════════

from typing import Protocol, runtime_checkable


@runtime_checkable
class ComposerLayerProtocol(Protocol):
    """Protocol that Composer layer aggregator must satisfy."""

    def build_layers(
        self,
        emotion: Dict[str, Any],
        memory: Any,
        inner_state: Dict[str, Any],
        relationship: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build context layers for LLM prompt composition."""
        ...


# ═══════════════════════════════════════════
# Router Provider Protocol
# ═══════════════════════════════════════════


@runtime_checkable
class RouterProviderProtocol(Protocol):
    """Protocol that LLM router must satisfy."""

    async def call_main(
        self,
        messages: list,
        temperature: float | None = None,
        max_tokens: int | None = None,
        agent_name: str = "unknown",
    ) -> str:
        """Call main model for quality responses."""
        ...

    async def call_cheap(
        self,
        messages: list,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        agent_name: str = "unknown",
    ) -> str:
        """Call cheap model for auxiliary tasks."""
        ...
