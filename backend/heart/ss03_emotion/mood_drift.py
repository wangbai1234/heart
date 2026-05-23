"""
Mood Drift Engine per SS03 §3.5 and §3.7.

Scheduled hourly drift of mood baseline based on recent emotion history,
Soul configuration, and environmental factors.

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def drift_mood(
    current_state: Dict[str, Any],
    soul: Dict[str, Any],
    hours_since_last: float = 1.0,
    days_since_last_interaction: float = 0.0,
    current_local_time: datetime | None = None,
) -> Dict[str, Any]:
    """
    Apply mood drift to EmotionState.

    Called by hourly scheduler per §3.5 Runtime Flow.

    Per spec:
    1. Compute 24h moving average of VAD from recent_vad_history
    2. Compute EWMA (Exponentially Weighted Moving Average)
    3. Apply Soul.mood_volatility:
       - High volatility: mood follows average quickly
       - Low volatility: mood drifts slowly toward Soul baseline
    4. Inject environmental factors (time of day, weekday)
    5. Inject longing gradient (grows with absence)
    6. Respect floor/ceiling bounds: |valence| ≤ 0.5 (mood is backdrop, not peak)

    Args:
        current_state: Current EmotionState dict with:
            - recent_vad_history: List[{vad: {v, a, d}, at: str, triggered_by: List}]
            - mood: {valence_baseline, arousal_baseline, dominance_baseline, ...}
        soul: Soul spec dict with:
            - cognitive_style.emotional_inertia.mood_volatility: float [0, 1]
            - baseline_mood: optional {valence, arousal, dominance}
        hours_since_last: Hours since last drift (default 1.0 for hourly)
        days_since_last_interaction: Days since user last interacted
        current_local_time: Current time (for environmental factors)

    Returns:
        Updated mood dict:
        {
            "valence_baseline": float,
            "arousal_baseline": float,
            "dominance_baseline": float,
            "background_emotions": List[str],
            "last_updated_at": str (ISO),
            "drift_history": List[{...}],
        }

    Target latency: P95 < 200ms per §10.4
    """
    if current_local_time is None:
        current_local_time = datetime.now(timezone.utc)

    mood = current_state.get("mood", {})
    recent_vad_history = current_state.get("recent_vad_history", [])

    # Current mood baseline
    current_mood_vad = {
        "valence": mood.get("valence_baseline", 0.0),
        "arousal": mood.get("arousal_baseline", 0.3),
        "dominance": mood.get("dominance_baseline", 0.5),
    }

    # Step 1: Compute 24h moving average from recent VAD history
    recent_average = _compute_24h_average(recent_vad_history)

    # Step 2: Compute EWMA (more weight on recent)
    ewma = _compute_ewma(recent_vad_history, alpha=0.3)

    # Step 3: Blend average and EWMA
    # Use 60% EWMA (recent matters more) + 40% average (stability)
    blended_vad = {
        "valence": 0.6 * ewma["valence"] + 0.4 * recent_average["valence"],
        "arousal": 0.6 * ewma["arousal"] + 0.4 * recent_average["arousal"],
        "dominance": 0.6 * ewma["dominance"] + 0.4 * recent_average["dominance"],
    }

    # Step 4: Apply Soul.mood_volatility
    mood_volatility = _get_mood_volatility(soul)
    soul_baseline = _get_soul_baseline_mood(soul)

    # High volatility: mood follows blended_vad quickly (α large)
    # Low volatility: mood drifts slowly toward soul_baseline (α small)
    # Formula: new_mood = current + volatility × (blended - current) + (1 - volatility) × rate × (soul_baseline - current)
    drift_rate_to_baseline = 0.05  # Slow drift toward Soul baseline per hour

    target_vad = {
        "valence": (
            current_mood_vad["valence"]
            + mood_volatility * (blended_vad["valence"] - current_mood_vad["valence"])
            + (1 - mood_volatility) * drift_rate_to_baseline * (soul_baseline["valence"] - current_mood_vad["valence"])
        ),
        "arousal": (
            current_mood_vad["arousal"]
            + mood_volatility * (blended_vad["arousal"] - current_mood_vad["arousal"])
            + (1 - mood_volatility) * drift_rate_to_baseline * (soul_baseline["arousal"] - current_mood_vad["arousal"])
        ),
        "dominance": (
            current_mood_vad["dominance"]
            + mood_volatility * (blended_vad["dominance"] - current_mood_vad["dominance"])
            + (1 - mood_volatility) * drift_rate_to_baseline * (soul_baseline["dominance"] - current_mood_vad["dominance"])
        ),
    }

    # Step 5: Inject environmental factors
    target_vad = _apply_environmental_factors(target_vad, current_local_time, soul)

    # Step 6: Inject longing gradient (grows with absence)
    target_vad = _apply_longing_gradient(target_vad, days_since_last_interaction, soul)

    # Step 7: Enforce floor/ceiling bounds
    # Per spec: mood baseline |valence| ≤ 0.5 (mood is backdrop, not peak)
    target_vad["valence"] = max(-0.5, min(0.5, target_vad["valence"]))
    target_vad["arousal"] = max(0.0, min(1.0, target_vad["arousal"]))
    target_vad["dominance"] = max(0.0, min(1.0, target_vad["dominance"]))

    # Determine background emotions from mood
    background_emotions = _derive_background_emotions(target_vad)

    # Update drift history
    drift_history = mood.get("drift_history", [])
    drift_history.append({
        "from": current_mood_vad,
        "to": target_vad,
        "at": current_local_time.isoformat(),
        "cause": {
            "recent_average": recent_average,
            "ewma": ewma,
            "volatility": mood_volatility,
            "environmental_applied": True,
            "longing_applied": days_since_last_interaction > 0,
        },
    })

    # Keep only last 50 drift history entries
    if len(drift_history) > 50:
        drift_history = drift_history[-50:]

    return {
        "valence_baseline": target_vad["valence"],
        "arousal_baseline": target_vad["arousal"],
        "dominance_baseline": target_vad["dominance"],
        "background_emotions": background_emotions,
        "last_updated_at": current_local_time.isoformat(),
        "drift_history": drift_history,
    }


def _compute_24h_average(recent_vad_history: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute simple moving average of VAD over last 24h.

    Returns:
        {"valence": float, "arousal": float, "dominance": float}
    """
    if not recent_vad_history:
        return {"valence": 0.0, "arousal": 0.3, "dominance": 0.5}

    # Filter to last 24h (if timestamps available)
    # For now, use all available history
    total_v = 0.0
    total_a = 0.0
    total_d = 0.0
    count = 0

    for entry in recent_vad_history:
        vad = entry.get("vad", {})
        total_v += vad.get("valence", 0.0)
        total_a += vad.get("arousal", 0.3)
        total_d += vad.get("dominance", 0.5)
        count += 1

    if count == 0:
        return {"valence": 0.0, "arousal": 0.3, "dominance": 0.5}

    return {
        "valence": total_v / count,
        "arousal": total_a / count,
        "dominance": total_d / count,
    }


def _compute_ewma(recent_vad_history: List[Dict[str, Any]], alpha: float = 0.3) -> Dict[str, float]:
    """
    Compute Exponentially Weighted Moving Average (EWMA).

    EWMA gives more weight to recent observations:
    EWMA_t = α × X_t + (1 - α) × EWMA_{t-1}

    Args:
        recent_vad_history: List of VAD snapshots (oldest first)
        alpha: Smoothing factor [0, 1]. Higher = more weight on recent.

    Returns:
        {"valence": float, "arousal": float, "dominance": float}
    """
    if not recent_vad_history:
        return {"valence": 0.0, "arousal": 0.3, "dominance": 0.5}

    # Initialize with first observation
    first_vad = recent_vad_history[0].get("vad", {})
    ewma_v = first_vad.get("valence", 0.0)
    ewma_a = first_vad.get("arousal", 0.3)
    ewma_d = first_vad.get("dominance", 0.5)

    # Apply EWMA formula
    for entry in recent_vad_history[1:]:
        vad = entry.get("vad", {})
        ewma_v = alpha * vad.get("valence", 0.0) + (1 - alpha) * ewma_v
        ewma_a = alpha * vad.get("arousal", 0.3) + (1 - alpha) * ewma_a
        ewma_d = alpha * vad.get("dominance", 0.5) + (1 - alpha) * ewma_d

    return {
        "valence": ewma_v,
        "arousal": ewma_a,
        "dominance": ewma_d,
    }


def _get_mood_volatility(soul: Dict[str, Any]) -> float:
    """
    Extract mood_volatility from Soul spec.

    Returns:
        Float in [0, 1] where:
        - 0.0 = very stable mood (ignores recent emotions, drifts to baseline)
        - 1.0 = very volatile mood (follows recent emotions closely)
        - Rin: 0.2 (stable)
        - Dorothy: 0.75 (volatile)
    """
    try:
        cognitive_style = soul.get("cognitive_style", {})
        emotional_inertia = cognitive_style.get("emotional_inertia", {})
        volatility = emotional_inertia.get("mood_volatility", 0.5)
        return max(0.0, min(1.0, float(volatility)))
    except (AttributeError, TypeError, ValueError):
        return 0.5


def _get_soul_baseline_mood(soul: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract baseline_mood from Soul spec.

    This is the "default" mood the character drifts toward in absence of input.

    Returns:
        {"valence": float, "arousal": float, "dominance": float}
    """
    baseline = soul.get("baseline_mood", {})
    return {
        "valence": baseline.get("valence", 0.0),
        "arousal": baseline.get("arousal", 0.3),
        "dominance": baseline.get("dominance", 0.5),
    }


def _apply_environmental_factors(
    vad: Dict[str, float],
    current_time: datetime,
    soul: Dict[str, Any],
) -> Dict[str, float]:
    """
    Apply environmental modifiers per §3.5 step 4.

    Factors:
    - Time of day: Late night (23:00-05:00) → arousal slightly lower
    - Weekday vs weekend: Weekend → valence slightly more positive

    Args:
        vad: Current target VAD
        current_time: Current datetime
        soul: Soul spec (for character-specific environmental sensitivity)

    Returns:
        Modified VAD
    """
    hour = current_time.hour
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday

    # Time of day modifier
    # Late night (23:00-05:00): arousal -0.05
    if hour >= 23 or hour <= 5:
        vad["arousal"] = max(0.0, vad["arousal"] - 0.05)

    # Weekend modifier (Saturday=5, Sunday=6)
    # Weekend: valence +0.02
    if weekday >= 5:
        vad["valence"] = min(0.5, vad["valence"] + 0.02)

    return vad


def _apply_longing_gradient(
    vad: Dict[str, float],
    days_since_last_interaction: float,
    soul: Dict[str, Any],
) -> Dict[str, float]:
    """
    Inject longing gradient per §3.5 step 5.

    Longing grows monotonically with user absence.
    Effect on mood:
    - Valence slightly negative (missing someone)
    - Arousal slightly elevated (anticipation/worry)

    Args:
        vad: Current target VAD
        days_since_last_interaction: Days since user last interacted
        soul: Soul spec (affects longing growth rate)

    Returns:
        Modified VAD
    """
    if days_since_last_interaction <= 0:
        return vad

    # Longing effect grows with time, capped at 7 days
    days_capped = min(days_since_last_interaction, 7.0)

    # Valence impact: -0.01 per day (up to -0.07)
    valence_impact = -0.01 * days_capped

    # Arousal impact: +0.005 per day (slight anticipation/worry)
    arousal_impact = 0.005 * days_capped

    vad["valence"] = max(-0.5, vad["valence"] + valence_impact)
    vad["arousal"] = min(1.0, vad["arousal"] + arousal_impact)

    return vad


def _derive_background_emotions(vad: Dict[str, float]) -> List[str]:
    """
    Derive background emotions from mood VAD.

    These are low-intensity emotions that color the mood baseline.

    Returns:
        List of emotion names (e.g., ["weariness", "longing"])
    """
    emotions = []

    valence = vad["valence"]
    arousal = vad["arousal"]

    # Negative valence + low arousal = weariness
    if valence < -0.2 and arousal < 0.4:
        emotions.append("weariness")

    # Negative valence + moderate arousal = longing/sadness
    if valence < -0.15 and 0.3 <= arousal <= 0.6:
        emotions.append("longing")

    # Positive valence + moderate arousal = contentment
    if valence > 0.2 and 0.3 <= arousal <= 0.5:
        emotions.append("contentment")

    # Low arousal regardless of valence = calmness
    if arousal < 0.3:
        emotions.append("calmness")

    return emotions
