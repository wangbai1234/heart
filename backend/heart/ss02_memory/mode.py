"""Memory extractor mode — feature flag for regex/llm/dual switching.

Controls how memory extraction is performed:
- "regex": Current behavior (fast path only, no LLM extraction)
- "llm": Slow path LLM extraction only (fast path writes L1 + enqueues)
- "dual": Both paths run; LLM writes to L3, regex writes to shadow table

Usage:
    from heart.ss02_memory.mode import get_mode
    mode = get_mode()
    if mode in ("llm", "dual"):
        # enqueue extraction
"""

from __future__ import annotations

from typing import Literal

from heart.core.config import settings

_MODE_VALUES = frozenset({"regex", "llm", "dual"})


def get_mode() -> Literal["regex", "llm", "dual"]:
    """Return the current memory extractor mode from settings.

    Returns:
        One of "regex", "llm", "dual".
    """
    raw = getattr(settings, "memory_extractor_mode", "regex")
    mode = raw.lower().strip()
    if mode not in _MODE_VALUES:
        raise ValueError(
            f"Invalid MEMORY_EXTRACTOR_MODE: {mode!r}. "
            f"Expected one of: {', '.join(sorted(_MODE_VALUES))}"
        )
    return mode  # type: ignore[return-value]


def is_llm_enabled() -> bool:
    """Return True if LLM extraction is active (llm or dual mode)."""
    return get_mode() in ("llm", "dual")


def is_regex_active() -> bool:
    """Return True if regex extraction is the primary path (regex or dual mode)."""
    return get_mode() in ("regex", "dual")
