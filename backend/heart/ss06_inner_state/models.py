"""
SS06 Inner State data models.

Defines InnerState (per user×character) and ProactiveMessage (outbound initiative).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
from uuid import UUID


@dataclass
class InnerState:
    """Per (user, character) inner state snapshot."""

    user_id: UUID
    character_id: str

    mood: float = 0.5
    energy: float = 0.7
    concerns: List[str] = field(default_factory=list)
    activities: List[str] = field(default_factory=list)
    unfinished_thoughts: List[str] = field(default_factory=list)

    last_tick_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ticks_today: int = 0
    proactives_today: int = 0


@dataclass
class ProactiveMessage:
    """A proactively-generated outbound message from the character."""

    user_id: UUID
    character_id: str
    content: str
    trigger_type: str  # scheduled, event_driven, anniversary, reunion
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered: bool = False
