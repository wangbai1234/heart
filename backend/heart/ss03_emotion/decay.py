"""
Emotion Decay Engine per SS03 §3.6 and §4.7.

Type-specific decay profiles:
- exponential: joy, excitement, surprise, anger
- logarithmic: sadness (slow initial decay)
- grows_with_absence: longing (increases over time)
- repair_required: aggrieved, coldness (needs explicit repair)
- almost_permanent: attachment (very slow decay)
- cyclic: weariness (circadian pattern)

Author: 心屿团队
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict


class DecayEngine:
    """
    Apply type-specific decay to emotions based on elapsed time.

    INV-E-7 compliance: Different emotions have different decay curves.
    """

    def __init__(self, decay_profiles: Dict[str, Any]):
        """
        Args:
            decay_profiles: Dictionary from emotion_lexicon.yaml decay_profiles section
        """
        self.profiles = decay_profiles
        self.default_profile = decay_profiles.get(
            "default",
            {
                "decay_type": "exponential",
                "half_life_hours": 4.0,
                "floor": 0.05,
            },
        )

    def apply_decay(
        self,
        emotion: str,
        current_intensity: float,
        delta_t_hours: float,
        repair_progress: float = 0.0,
        **kwargs: Any,
    ) -> float:
        """
        Apply decay to emotion based on time elapsed.

        Args:
            emotion: Emotion name (e.g., "joy", "aggrieved")
            current_intensity: Current intensity [0, 1]
            delta_t_hours: Time elapsed since last update (hours)
            repair_progress: Repair progress [0, 1] for repair_required emotions
            **kwargs: Additional context (e.g., current_local_time for cyclic)

        Returns:
            New intensity after decay [0, 1]

        Invariants:
            - Returns value in [0, 1]
            - For repair_required: natural decay is slow without repair
            - For grows_with_absence: intensity increases
        """
        if delta_t_hours <= 0:
            return current_intensity

        profile = self.profiles.get(emotion, self.default_profile)
        decay_type = profile.get("decay_type", "exponential")

        if decay_type == "exponential":
            return self._exponential_decay(current_intensity, delta_t_hours, profile)
        elif decay_type == "logarithmic":
            return self._logarithmic_decay(current_intensity, delta_t_hours, profile)
        elif decay_type == "grows_with_absence":
            return self._grows_with_absence(current_intensity, delta_t_hours, profile)
        elif decay_type == "repair_required":
            return self._repair_required_decay(
                current_intensity, delta_t_hours, repair_progress, profile
            )
        elif decay_type == "almost_permanent":
            return self._almost_permanent_decay(current_intensity, delta_t_hours, profile)
        elif decay_type == "cyclic":
            return self._cyclic_decay(current_intensity, kwargs.get("current_local_time"))
        else:
            # Fallback to exponential
            return self._exponential_decay(current_intensity, delta_t_hours, profile)

    def _exponential_decay(
        self,
        intensity: float,
        delta_t_hours: float,
        profile: Dict[str, Any],
    ) -> float:
        """
        Exponential decay: I(t) = I₀ × 0.5^(Δt / half_life)

        §4.7 formula for emotions like joy, excitement.
        """
        half_life = profile.get("half_life_hours", 4.0)
        floor = profile.get("floor", 0.05)

        new_intensity = intensity * (0.5 ** (delta_t_hours / half_life))
        return max(floor, new_intensity)

    def _logarithmic_decay(
        self,
        intensity: float,
        delta_t_hours: float,
        profile: Dict[str, Any],
    ) -> float:
        """
        Logarithmic decay: slower at the beginning.
        Used for sadness (一开始衰减慢).

        Formula: I(t) = I₀ × (1 - log_factor × 0.5)
        where log_factor = log(1 + Δt) / log(1 + half_life)
        """
        half_life = profile.get("half_life_hours", 12.0)
        floor = profile.get("floor", 0.1)

        if delta_t_hours < 1:
            # Very slow initial decay
            return intensity * 0.98

        log_factor = math.log(1 + delta_t_hours) / math.log(1 + half_life)
        new_intensity = intensity * (1 - log_factor * 0.5)
        return max(floor, new_intensity)

    def _grows_with_absence(
        self,
        intensity: float,
        delta_t_hours: float,
        profile: Dict[str, Any],
    ) -> float:
        """
        Grows with absence: intensity increases over time.
        Used for longing (想念).

        Formula: I(t) = I₀ + growth_rate × Δt_days
        """
        growth_rate = profile.get("growth_rate", 0.05)  # per day
        cap = profile.get("cap", 1.0)

        delta_days = delta_t_hours / 24.0
        new_intensity = intensity + (growth_rate * delta_days)
        return min(cap, new_intensity)

    def _repair_required_decay(
        self,
        intensity: float,
        delta_t_hours: float,
        repair_progress: float,
        profile: Dict[str, Any],
    ) -> float:
        """
        Repair-required decay: natural decay is very slow, repair has strong effect.
        Used for aggrieved, coldness.

        §4.7: take minimum of (natural_decay, repair_decay)

        INV-E-6: intensity_decay_without_repair < intensity_decay_with_repair × 0.3
        """
        natural_half_life = profile.get("natural_half_life_hours", 168.0)  # 7 days

        # Natural decay: extremely slow
        natural_decay = intensity * (0.5 ** (delta_t_hours / natural_half_life))

        # Repair decay: repair_progress reduces intensity
        repair_decay = intensity * (1 - repair_progress * 0.8)

        # Take the smaller (more "repaired") value
        return min(natural_decay, repair_decay)

    def _almost_permanent_decay(
        self,
        intensity: float,
        delta_t_hours: float,
        profile: Dict[str, Any],
    ) -> float:
        """
        Almost permanent decay: very slow, for long-term baseline emotions.
        Used for attachment.
        """
        half_life_days = profile.get("half_life_days", 90.0)
        floor = profile.get("floor", 0.3)

        half_life_hours = half_life_days * 24
        new_intensity = intensity * (0.5 ** (delta_t_hours / half_life_hours))
        return max(floor, new_intensity)

    def _cyclic_decay(
        self,
        intensity: float,
        current_local_time: datetime | None,
    ) -> float:
        """
        Cyclic decay: follows circadian pattern.
        Used for weariness (疲惫).

        Peak at late night, low at midday.
        """
        if current_local_time is None:
            return intensity

        hour = current_local_time.hour

        # Circadian modulator: 0-1 scale
        # Peak at 23:00-02:00 (night), low at 12:00-14:00 (midday)
        if 23 <= hour or hour <= 2:
            modulator = 1.0  # Peak weariness
        elif 12 <= hour <= 14:
            modulator = 0.3  # Low weariness
        elif 6 <= hour <= 10:
            modulator = 0.5  # Morning
        elif 18 <= hour <= 22:
            modulator = 0.7  # Evening
        else:
            modulator = 0.6  # Default

        # Intensity drifts toward modulator
        target = modulator
        drift_rate = 0.2  # How fast it drifts per application
        new_intensity = intensity + (target - intensity) * drift_rate

        return max(0.0, min(1.0, new_intensity))


def apply_decay_to_stack(
    active_stack: list[Dict[str, Any]],
    delta_t_hours: float,
    decay_engine: DecayEngine,
    current_local_time: datetime | None = None,
) -> list[Dict[str, Any]]:
    """
    Apply decay to all emotions in active_stack.

    Args:
        active_stack: List of ActiveEmotion dicts
        delta_t_hours: Time elapsed since last update
        decay_engine: DecayEngine instance
        current_local_time: Current local time (for cyclic emotions)

    Returns:
        Updated active_stack with decayed intensities.
        Emotions with intensity < 0.05 are removed.

    Invariants:
        - INV-E-2: |active_stack| ≤ MAX_CONCURRENT_EMOTIONS (enforced elsewhere)
        - INV-E-3: ∀ emotion e, e.intensity ∈ [0, 1]
    """
    updated_stack = []

    for emotion_entry in active_stack:
        emotion_name = emotion_entry["emotion"]
        current_intensity = emotion_entry["intensity"]
        repair_progress = emotion_entry.get("repair_progress", 0.0)

        new_intensity = decay_engine.apply_decay(
            emotion=emotion_name,
            current_intensity=current_intensity,
            delta_t_hours=delta_t_hours,
            repair_progress=repair_progress,
            current_local_time=current_local_time,
        )

        # Filter out emotions below threshold
        if new_intensity >= 0.05:
            emotion_entry["intensity"] = new_intensity
            updated_stack.append(emotion_entry)

    return updated_stack
