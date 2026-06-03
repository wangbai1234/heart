"""
SS04: Relationship Phase Engine

Implements relationship state tracking, stage transitions, and dimension updates.

Core components:
- StagePhaseEngine: Stage transition state machine
- TrustTracker: Trust dimension updates
- AttachmentTracker: Attachment dimension updates
- RelationshipService: Orchestration and persistence
- SignalAggregator: Signal aggregation with anti-gaming dedup (v1.1)
- DistinctSessionTracker: Per-session event counting (v1.1)
- SignalCooldownTracker: Cooldown between repeated signals (v1.1)

Author: 心屿团队
Tuning: v1.1 (2026-05-21)
"""

from .anti_gaming import (
    DistinctSessionTracker,
    SignalCooldownTracker,
    is_empty_message,
)
from .attachment_tracker import AttachmentTracker
from .models import RelationshipEvent, RelationshipState
from .service import RelationshipService
from .signal_aggregator import SignalAggregator, create_signal_aggregator
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
    # Signal Aggregation (v1.1)
    "SignalAggregator",
    "create_signal_aggregator",
    # Anti-Gaming (v1.1)
    "DistinctSessionTracker",
    "SignalCooldownTracker",
    "is_empty_message",
    # Service
    "RelationshipService",
]
