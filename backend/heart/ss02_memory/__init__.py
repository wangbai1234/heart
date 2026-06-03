"""
SS02 Memory Runtime - Subsystem Exports

Covers:
- L2/L3/L4 Memory Models
- Decay Engine (importance decay + reinforcement)
- Memory Encoder Worker (阶段 2 LLM extraction)
- Multi-Strategy Retriever (vector + graph + recency + emotional + identity)
- Memory Reconstructor (state-aware recall with voice_dna)
- Forgetting Affect Engine (inject "she's forgetting" hints)

Author: 心屿团队
"""

from .decay_engine import DecayEngine, ReinforcementTrigger, reinforce_memory
from .forgetting_affect import (
    ForgettingAffectConfig,
    ForgettingAffectDecision,
    ForgettingAffectEngine,
    InjectionMode,
    MemoryStateDistribution,
)
from .models import EpisodicMemory, FactNode, IdentityMemory, MemoryEncodingEvent
from .reconstructor import Reconstructor, ReconstructResult
from .retriever import (
    EmotionalRetriever,
    GraphRetriever,
    IdentityLookup,
    MemoryRetrievalResult,
    QueryContext,
    RecencyRetriever,
    RetrievalOrchestrator,
    ScoredMemory,
    VectorRetriever,
)

__all__ = [
    # Models
    "EpisodicMemory",
    "FactNode",
    "IdentityMemory",
    "MemoryEncodingEvent",
    # Decay Engine
    "DecayEngine",
    "reinforce_memory",
    "ReinforcementTrigger",
    # Retriever
    "RetrievalOrchestrator",
    "VectorRetriever",
    "GraphRetriever",
    "RecencyRetriever",
    "EmotionalRetriever",
    "IdentityLookup",
    "QueryContext",
    "ScoredMemory",
    "MemoryRetrievalResult",
    # Reconstructor
    "Reconstructor",
    "ReconstructResult",
    # Forgetting Affect Engine
    "ForgettingAffectEngine",
    "ForgettingAffectConfig",
    "ForgettingAffectDecision",
    "InjectionMode",
    "MemoryStateDistribution",
]
