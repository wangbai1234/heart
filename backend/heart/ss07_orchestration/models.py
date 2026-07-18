"""
SS07 Orchestration data models — per docs/design/orchestrator_min_viable.md §3.2.

Defines the interface contracts for Orchestrator, SessionManager, and CircuitBreaker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID


@dataclass
class TurnRequest:
    """Inbound turn request from the API layer."""

    user_id: UUID
    character_id: str
    user_message: str
    history: list[dict]  # [{"role": "user/assistant", "content": "..."}, ...]
    trace_id: UUID
    modality: str = "text"
    # Requested LLM model; orchestrator/composer will use stream_for with failover.
    # Defaults to "deepseek" (free tier default).
    model: str = "deepseek"


@dataclass
class TurnResponse:
    """Outbound turn response from the orchestrator."""

    response: str
    character_id: str
    trace_id: UUID
    path: Literal["normal", "care", "reject", "fallback"]
    safety_severity: Optional[str] = None  # GREEN / YELLOW / ... / PURPLE


@dataclass
class Session:
    """Per user × character conversation session.

    Persisted to the sessions DB table via SessionManager.
    """

    session_id: UUID
    user_id: UUID
    character_id: str
    started_at: datetime
    last_activity_at: datetime
    turn_count: int
    suicide_protocol_active: bool = False

    @property
    def is_active(self) -> bool:
        return True  # sessions never expire in MVP; future: check last_activity_at
