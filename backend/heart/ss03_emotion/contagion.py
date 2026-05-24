"""
Contagion Engine per SS03 §3.5 and §10.3.

User emotion transmission to character, modulated by Soul configuration.

Author: 心屿团队
"""

from __future__ import annotations

from typing import Any, Dict


def apply_contagion(
    user_emotion_vad: Dict[str, float],
    current_state: Dict[str, Any],
    soul: Dict[str, Any],
    relationship_phase: str,
) -> Dict[str, float]:
    """
    Compute contagion delta from user emotion to character.

    Per §10.3 Contagion Engine:
    Δvalence_contagion = (user.valence - current.valence)
                        × (1 - shock_resistance)
                        × phase_modifier
                        × 0.15

    This is Soul-aware: reads shock_resistance from
    soul.cognitive_style.emotional_inertia.shock_resistance

    Args:
        user_emotion_vad: User's VAD (from fast encoder)
            {"valence": float, "arousal": float, "dominance": float}
        current_state: Current EmotionState dict
        soul: Soul spec dict with cognitive_style structure
        relationship_phase: Current relationship phase
            Options: stranger, acquaintance, friend, close_friend,
                     romantic, bonded

    Returns:
        VAD delta to apply:
        {"valence": float, "arousal": float, "dominance": float}

    Examples:
        >>> # Rin (high shock_resistance = 0.75)
        >>> soul_rin = {
        ...     "cognitive_style": {
        ...         "emotional_inertia": {"shock_resistance": "high"}
        ...     }
        ... }
        >>> user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}
        >>> state = {
        ...     "vad_valence": 0.0, "vad_arousal": 0.3, "vad_dominance": 0.5
        ... }
        >>> delta = apply_contagion(user_vad, state, soul_rin, "close_friend")
        >>> # Small delta due to high shock_resistance
        >>> assert abs(delta["valence"]) < 0.05

        >>> # Dorothy (low shock_resistance = 0.2)
        >>> soul_dorothy = {
        ...     "cognitive_style": {
        ...         "emotional_inertia": {"shock_resistance": "low"}
        ...     }
        ... }
        >>> delta = apply_contagion(user_vad, state, soul_dorothy, "close_friend")
        >>> # Larger delta due to low shock_resistance
        >>> assert abs(delta["valence"]) > 0.05
    """
    # Extract shock_resistance from Soul
    shock_resistance = _get_shock_resistance(soul)

    # Phase modifier (closer relationship = stronger contagion)
    phase_modifiers = {
        "stranger": 0.3,
        "acquaintance": 0.5,
        "friend": 0.7,
        "close_friend": 0.85,
        "romantic": 0.95,
        "bonded": 1.0,
    }
    phase_modifier = phase_modifiers.get(relationship_phase, 0.5)

    # Contagion strength
    strength = (1 - shock_resistance) * phase_modifier

    current_vad = {
        "valence": current_state.get("vad_valence", 0.0),
        "arousal": current_state.get("vad_arousal", 0.3),
        "dominance": current_state.get("vad_dominance", 0.5),
    }

    # Apply contagion with dampening factors
    # Valence and arousal transfer, but dominance does not
    delta_v = (user_emotion_vad["valence"] - current_vad["valence"]) * strength * 0.15
    delta_a = (user_emotion_vad["arousal"] - current_vad["arousal"]) * strength * 0.10
    delta_d = 0.0  # Dominance does not easily transfer per spec

    return {
        "valence": delta_v,
        "arousal": delta_a,
        "dominance": delta_d,
    }


def _get_shock_resistance(soul: Dict[str, Any]) -> float:
    """
    Extract shock_resistance from Soul spec.

    Soul.cognitive_style.emotional_inertia.shock_resistance can be:
    - String: "high", "medium", "low"
    - Float: [0, 1]

    Returns:
        Float in [0, 1] where:
        - 0.0 = no resistance (fully empathetic, like Dorothy)
        - 1.0 = complete resistance (no contagion)
        - Rin: 0.75 (high)
        - Dorothy: 0.2 (low)
    """
    try:
        cognitive_style = soul.get("cognitive_style", {})
        emotional_inertia = cognitive_style.get("emotional_inertia", {})
        shock_resistance = emotional_inertia.get("shock_resistance", "medium")

        # If already a float, return it
        if isinstance(shock_resistance, (int, float)):
            return max(0.0, min(1.0, float(shock_resistance)))

        # If string, map to float
        resistance_map = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.75,
        }

        return resistance_map.get(shock_resistance.lower(), 0.5)

    except (AttributeError, TypeError, KeyError):
        # Fallback: medium resistance
        return 0.5


def compute_empathy_curve(
    soul: Dict[str, Any],
    relationship_phase: str,
) -> float:
    """
    Compute empathy curve strength for this Soul at current relationship phase.

    This is the combined multiplier that determines how strongly user emotion
    affects the character.

    Returns:
        Float in [0, 1] representing empathy strength
        - 0.0 = no empathy (no contagion)
        - 1.0 = full empathy (maximum contagion)

    Examples:
        >>> # Rin as stranger: very low empathy
        >>> soul_rin = {"cognitive_style": {"emotional_inertia": {"shock_resistance": "high"}}}
        >>> empathy = compute_empathy_curve(soul_rin, "stranger")
        >>> assert empathy < 0.1

        >>> # Dorothy as romantic partner: high empathy
        >>> soul_dorothy = {"cognitive_style": {"emotional_inertia": {"shock_resistance": "low"}}}
        >>> empathy = compute_empathy_curve(soul_dorothy, "romantic")
        >>> assert empathy > 0.7
    """
    shock_resistance = _get_shock_resistance(soul)

    phase_modifiers = {
        "stranger": 0.3,
        "acquaintance": 0.5,
        "friend": 0.7,
        "close_friend": 0.85,
        "romantic": 0.95,
        "bonded": 1.0,
    }
    phase_modifier = phase_modifiers.get(relationship_phase, 0.5)

    return (1 - shock_resistance) * phase_modifier
