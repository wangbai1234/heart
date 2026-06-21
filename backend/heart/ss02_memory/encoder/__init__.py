"""
SS02 Memory Runtime - Encoding Pipeline.

Covers:
- Fast Heuristic Encoder (阶段 1: < 50ms)
- LLM Encoder Worker (阶段 2: async)

Author: 心屿团队
"""

from heart.ss02_memory.service import IdentitySignal as _IdentitySignal

from .fast import FastEncoder

__all__ = ["FastEncoder", "IdentitySignal"]

# ── Deprecated re-exports ────────────────────────────────────────


def __getattr__(name: str):
    if name == "IdentitySignal":
        import warnings

        warnings.warn(
            "IdentitySignal is deprecated. Use heart.ss02_memory.hints.Hint instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _IdentitySignal
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
