"""Memory extractor mode — feature flag for regex/llm/dual switching.

Controls how memory extraction is performed:
- "llm": (default) Slow path LLM extraction only (fast path writes L1 + enqueues)
- "regex": (deprecated) Fast path only, no LLM extraction. Will be removed.
- "dual": (deprecated) Both paths run; LLM writes to L3, regex writes to shadow.

Usage:
    from heart.ss02_memory.mode import get_mode
    mode = get_mode()
    if mode in ("llm", "dual"):
        # enqueue extraction

Deprecation timeline (Phase D §5.3):
    2026-06-19: default → "llm"; "regex"/"dual" emit deprecation warnings
    2026-10-17: full removal of RegexHintsProvider + Hint types
"""

from __future__ import annotations

from typing import Literal

import structlog

from heart.core.config import settings

logger = structlog.get_logger()

_MODE_VALUES = frozenset({"regex", "llm", "dual"})
_DEPRECATED_MODES: frozenset[str] = frozenset({"regex", "dual"})


def get_mode() -> Literal["regex", "llm", "dual"]:
    """Return the current memory extractor mode from settings.

    Returns:
        One of "regex", "llm", "dual".

    Deprecated:
        "regex" and "dual" modes.  Default is now "llm".
    """
    raw = getattr(settings, "memory_extractor_mode", "llm")
    mode = raw.lower().strip()
    if mode not in _MODE_VALUES:
        raise ValueError(
            f"Invalid MEMORY_EXTRACTOR_MODE: {mode!r}. "
            f"Expected one of: {', '.join(sorted(_MODE_VALUES))}"
        )

    if mode in _DEPRECATED_MODES:
        logger.warning(
            "memory_extractor_mode_deprecated",
            mode=mode,
            message=(
                f"MEMORY_EXTRACTOR_MODE={mode} is deprecated. "
                "Default is now 'llm'. "
                "Regex/dual modes will be removed per Phase D §5.3."
            ),
        )

    return mode  # type: ignore[return-value]


def is_llm_enabled() -> bool:
    """Return True if LLM extraction is active (llm or dual mode)."""
    return get_mode() in ("llm", "dual")


def is_regex_active() -> bool:
    """Return True if regex extraction is the primary path (regex or dual mode).

    Deprecated: regex extraction paths will be removed.
    """
    return get_mode() in ("regex", "dual")
