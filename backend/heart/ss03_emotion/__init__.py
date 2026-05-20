"""
SS03 Emotion State Machine.

Core components:
- EmotionService: Main orchestrator and single source of truth
- EmotionStateMachine: State transition logic
- TriggerDetector: Heuristic trigger detection
- DecayEngine: Type-specific emotion decay
- Contagion: User emotion transmission (Soul-aware)
- MoodDrift: Hourly mood baseline drift
- RepairEngine: Repair Mechanic for repair_required emotions

Author: 心屿团队
"""

from heart.ss03_emotion.contagion import apply_contagion, compute_empathy_curve
from heart.ss03_emotion.decay import DecayEngine, apply_decay_to_stack
from heart.ss03_emotion.mood_drift import drift_mood
from heart.ss03_emotion.repair import RepairEngine
from heart.ss03_emotion.service import EmotionService
from heart.ss03_emotion.state_machine import EmotionStateMachine
from heart.ss03_emotion.trigger_detector import TriggerDetector

__all__ = [
    "EmotionService",
    "EmotionStateMachine",
    "TriggerDetector",
    "DecayEngine",
    "RepairEngine",
    "apply_contagion",
    "compute_empathy_curve",
    "apply_decay_to_stack",
    "drift_mood",
]
