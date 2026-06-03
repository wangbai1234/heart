"""
SS06 Inner State + Behavior Runtime.

Manages per-character inner state (mood, energy, concerns),
periodic inner-loop ticks, and proactive outbound message generation.

Public API:
    InnerStateService  — tick(), get_proactive_messages(), get_inner_state()
    InnerState         — per (user×character) state snapshot
    ProactiveMessage   — outbound proactive message
"""

from .models import InnerState, ProactiveMessage
from .service import InnerStateService

__all__ = ["InnerStateService", "InnerState", "ProactiveMessage"]
