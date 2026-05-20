"""
SS04: Relationship Phase Engine

Implements relationship state tracking, stage transitions, and dimension updates.

Core components:
- StagePhaseEngine: Stage transition state machine
- TrustTracker: Trust dimension updates
- AttachmentTracker: Attachment dimension updates
- RelationshipService: Orchestration and persistence

Author: 心屿团队
"""

from .attachment_tracker import AttachmentTracker
from .models import RelationshipEvent, RelationshipState
from .service import RelationshipService
from .stage_engine import (
    RelationshipStage,
    Signal,
    SignalBatch,
    StageDecision,
    StagePhaseEngine,
    TransitionAction,
)
from .trust_tracker import TrustTracker

__all__ = [
    # Models
    "RelationshipState",
    "RelationshipEvent",
    # Stage Engine
    "StagePhaseEngine",
    "RelationshipStage",
    "TransitionAction",
    "StageDecision",
    "Signal",
    "SignalBatch",
    # Trackers
    "TrustTracker",
    "AttachmentTracker",
    # Service
    "RelationshipService",
]
