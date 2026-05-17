"""
Memory Retriever - SS02 §3.5 + §10.3

Multi-strategy retrieval system with parallel execution.

Exports:
- RetrievalOrchestrator: Main retrieval coordinator
- Individual strategies: VectorRetriever, GraphRetriever, etc.
- Data structures: QueryContext, ScoredMemory, MemoryRetrievalResult

Author: 心屿团队
"""

from .base import (
    MemoryRetrievalResult,
    QueryContext,
    RetrievalStrategy,
    ScoredMemory,
    combine_scores,
    select_top_k,
    DEFAULT_WEIGHTS,
)
from .emotional import EmotionalRetriever
from .graph import GraphRetriever
from .identity import IdentityLookup
from .orchestrator import RetrievalOrchestrator
from .recency import RecencyRetriever
from .vector import VectorRetriever

__all__ = [
    # Orchestrator
    "RetrievalOrchestrator",
    # Strategies
    "VectorRetriever",
    "GraphRetriever",
    "RecencyRetriever",
    "EmotionalRetriever",
    "IdentityLookup",
    # Base
    "RetrievalStrategy",
    "QueryContext",
    "ScoredMemory",
    "MemoryRetrievalResult",
    "combine_scores",
    "select_top_k",
    "DEFAULT_WEIGHTS",
]
