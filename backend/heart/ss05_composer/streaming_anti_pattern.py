"""
Streaming Anti-Pattern Pre-Filter — SS05 §3.3 step 8 (§3.5 + §10.4)

Watches LLM streaming chunks as they arrive and halts the stream before any
``hard_never`` literal reaches the user.  Works in tandem with the post-stream
``AntiPatternFilter`` (step 9) which remains the system-of-record for INV-PC-3.

Design: see docs/design/streaming_anti_pattern.md.

Architecture (per the design doc):
- Two sliding character buffers: ``scan_window`` for detection, ``hold_window``
  for unreleased tail.
- On each chunk arrival: append to both buffers → run Aho-Corasick on the
  scan tail → if match, halt stream immediately (drop hold, signal reroll).
  Characters age past ``hold_window`` are yielded to the user.
- On stream completion: flush the hold through the sync ``AntiPatternFilter``
  BEFORE releasing to the user (§3 design: closeable spec gap).
- Empty ``hard_never`` set → pass-through (zero overhead).
- Per-chunk scan < 5 ms budget (§3.3).

Constraints from the spec:
  PC-5:    Streaming output cannot be rewritten post-process.
  INV-PC-3: No released response may match soul.anti_patterns.hard_never.
  PCR-8:   Streaming does not retry already-sent content → reroll from zero.

Author: 心屿团队
"""

from __future__ import annotations

import structlog
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from heart.ss05_composer.anti_pattern_filter import (
    AHOCORASICK_AVAILABLE,
    AntiPatternFilter,
)

logger = structlog.get_logger()

# ============================================================
# Constants
# ============================================================

# Recommended max literal length per §2 design doc.
_MAX_RECOMMENDED_LITERAL_LENGTH = 40

# Safety margin added to max_pattern_length for scan_window (§2).
_SCAN_WINDOW_PAD = 32

# Default hold window minimum (§2, §10.4).
_MIN_HOLD_WINDOW = 50


# ============================================================
# Data types
# ============================================================


@dataclass
class PreFilterHalt:
    """Emitted when the pre-filter detects a hard_never literal mid-stream.

    This is the signal to cancel the LLM call, drop all buffered content,
    and initiate a reroll.  Nothing in the hold buffer ever reaches the user.
    """

    pattern: str
    """The literal that triggered the halt."""

    chars_received_before_halt: int
    """Total characters received from the LLM before detection."""

    chars_held_at_halt: int
    """Characters in the hold buffer at halt moment (never released)."""

    chunk_index: int
    """Which chunk triggered the halt (0-indexed)."""


@dataclass
class PreFilterStats:
    """Accumulated per-turn stats for observability (§4 metrics).

    All counters are reset per turn.
    """

    chunks_scanned: int = 0
    total_chars_scanned: int = 0
    scan_total_us: int = 0
    halted: bool = False
    halt_info: Optional[PreFilterHalt] = None

    @property
    def avg_scan_us(self) -> float:
        if self.chunks_scanned == 0:
            return 0.0
        return self.scan_total_us / self.chunks_scanned


# ============================================================
# StreamingPreFilter
# ============================================================


class StreamingPreFilter:
    """Streaming hard_never pre-filter for LLM output chunks.

    Shares the same ``ahocorasick.Automaton`` as the post-stream
    ``AntiPatternFilter`` so both filters use the exact same pattern set.

    Usage::

        # Build once per (character_id, spec_version), reuse across turns.
        sync_filter = AntiPatternFilter(soul)
        pre = StreamingPreFilter.from_sync_filter(sync_filter)

        async for chunk in llm_stream:
            for user_text in pre.feed(chunk):
                yield user_text   # safe to show user
            if pre.halted:
                await llm_stream.aclose()
                return RerollSignal(matcher=pre.halt_info.pattern)

        # Stream complete — flush hold through step 9 BEFORE releasing.
        for user_text in pre.flush(sync_filter):
            yield user_text
    """

    # ----------------------------------------------------------
    # Construction
    # ----------------------------------------------------------

    def __init__(
        self,
        automaton,
        *,
        hard_never_literals: Optional[list[str]] = None,
        max_pattern_length: int = 0,
        hold_window: int = _MIN_HOLD_WINDOW,
        scan_window: Optional[int] = None,
    ):
        """Create a pre-filter for one streaming turn.

        Prefer ``from_sync_filter()`` for production use; this constructor
        is mainly for testing with custom window sizes.

        Args:
            automaton: A compiled ``ahocorasick.Automaton`` (may be None
                if pyahocorasick is unavailable or the hard_never set is empty).
            hard_never_literals: Raw literal strings for the O(n*m) fallback
                path when pyahocorasick is unavailable.
            max_pattern_length: Longest literal (chars).  Used to compute
                ``scan_window`` default.
            hold_window: Characters to hold before releasing to user.
                Must be >= max(max_pattern_length, _MIN_HOLD_WINDOW).
            scan_window: Characters to scan on each chunk.  Defaults to
                ``max_pattern_length + _SCAN_WINDOW_PAD``.
        """
        self._ac = automaton
        self._hard_never_literals = hard_never_literals or []
        self._max_pattern_length = max_pattern_length
        self._hold_window = max(hold_window, _MIN_HOLD_WINDOW)
        self._scan_window = (
            scan_window
            if scan_window is not None
            else max_pattern_length + _SCAN_WINDOW_PAD
        )

        # Per-turn mutable state
        self._scan_buffer: str = ""
        self._hold_buffer: str = ""
        self._released: list[str] = []
        self._chunk_index: int = 0
        self._total_chars_received: int = 0
        self._halted: bool = False
        self._halt_info: Optional[PreFilterHalt] = None

        # Startup safety check per §5: warn on long literals
        if self._hard_never_literals:
            for literal in self._hard_never_literals:
                if len(literal) > _MAX_RECOMMENDED_LITERAL_LENGTH:
                    logger.warning(
                        "StreamingPreFilter: hard_never literal exceeds %d chars "
                        "(%d chars: '%s...'). Consider reclassifying as "
                        "forbidden_pattern.",
                        _MAX_RECOMMENDED_LITERAL_LENGTH,
                        len(literal),
                        literal[:_MAX_RECOMMENDED_LITERAL_LENGTH],
                    )

    @classmethod
    def from_sync_filter(
        cls,
        sync_filter: AntiPatternFilter,
        *,
        hold_window: int = _MIN_HOLD_WINDOW,
    ) -> "StreamingPreFilter":
        """Build from the post-stream AntiPatternFilter.

        Shares the same Aho-Corasick automaton so both filters use the
        identical ``hard_never`` pattern set (§3 streaming design).

        Args:
            sync_filter: An already-constructed AntiPatternFilter whose
                automaton and pattern list will be shared.
            hold_window: Override the default hold window size.
        """
        max_len = sync_filter.max_pattern_length
        effective_hold = max(hold_window, _MIN_HOLD_WINDOW)
        # If the longest literal exceeds the hold window, widen it.
        if max_len > effective_hold:
            logger.warning(
                "StreamingPreFilter: max_pattern_length=%d > hold_window=%d; "
                "widening hold_window to %d.",
                max_len,
                effective_hold,
                max_len,
            )
            effective_hold = max_len
        return cls(
            automaton=sync_filter.automaton,
            hard_never_literals=sync_filter.hard_never_literals,
            max_pattern_length=max_len,
            hold_window=effective_hold,
        )

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------

    @property
    def halted(self) -> bool:
        """True if the pre-filter has halted the stream (reroll needed)."""
        return self._halted

    @property
    def halt_info(self) -> Optional[PreFilterHalt]:
        """Detailed halt information, or None if not halted."""
        return self._halt_info

    @property
    def is_pass_through(self) -> bool:
        """True when there are no hard_never literals to scan (optimisation)."""
        return self._ac is None and not self._hard_never_literals

    @property
    def stats(self) -> PreFilterStats:
        """Accumulated per-turn stats."""
        s = PreFilterStats(
            chunks_scanned=self._chunk_index,
            total_chars_scanned=self._total_chars_received,
            halted=self._halted,
            halt_info=self._halt_info,
        )
        return s

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def feed(self, chunk: str) -> list[str]:
        """Process one chunk from the LLM stream.

        Appends *chunk* to both buffers, scans for ``hard_never`` literals,
        and returns any characters that have aged past the hold window
        (safe to release to user).

        If a literal is detected, sets ``self.halted = True`` and returns
        an empty list — nothing in the hold buffer is ever released.

        Args:
            chunk: A decoded UTF-8 string from the LLM stream.

        Returns:
            List of character strings safe to yield to the user.
            Each element is typically a single character for streaming
            granularity; callers may join them.
        """
        if self._halted:
            return []

        self._chunk_index += 1
        chunk_len = len(chunk)
        if chunk_len == 0:
            return []

        self._total_chars_received += chunk_len

        # Pass-through optimisation: no patterns → release immediately
        if self.is_pass_through:
            self._released.extend(chunk)
            return list(chunk)

        # Append to both buffers
        self._scan_buffer += chunk
        self._hold_buffer += chunk

        # --- Scan for violations ---
        t0 = time.perf_counter()
        matched = self._scan_for_patterns()
        scan_us = int((time.perf_counter() - t0) * 1_000_000)

        if matched is not None:
            self._halted = True
            self._halt_info = PreFilterHalt(
                pattern=matched,
                chars_received_before_halt=self._total_chars_received,
                chars_held_at_halt=len(self._hold_buffer),
                chunk_index=self._chunk_index,
            )
            logger.info(
                "StreamingPreFilter: halted on pattern '%s' at chunk %d, "
                "%d chars received, %d held.",
                matched,
                self._chunk_index,
                self._total_chars_received,
                len(self._hold_buffer),
            )
            return []

        # --- Release aged characters ---
        released_chars = self._release_aged()
        return released_chars

    def flush(self, sync_filter: AntiPatternFilter) -> list[str]:
        """Final flush after the LLM stream completes.

        Runs the hold buffer through the sync ``AntiPatternFilter`` BEFORE
        releasing to the user (§3 design: closeable spec gap).  If the sync
        filter detects a violation, returns an empty list and logs a gap
        event (step-9 caught what step-8 missed).

        Args:
            sync_filter: The post-stream AntiPatternFilter instance.

        Returns:
            Characters safe to release from the final hold buffer.
        """
        if self._halted:
            return []

        hold = self._hold_buffer
        if not hold:
            return []

        # Run step 9 on the final hold before releasing.
        result = sync_filter.filter(hold)
        if not result.passed:
            logger.warning(
                "StreamingPreFilter.flush: step-9 caught violation(s) in final "
                "hold buffer that step-8 missed: %s",
                [v.pattern for v in result.violations],
            )
            # Gap event: step-9 caught what we missed.
            self._halted = True
            self._halt_info = PreFilterHalt(
                pattern=",".join(v.pattern for v in result.violations),
                chars_received_before_halt=self._total_chars_received,
                chars_held_at_halt=len(hold),
                chunk_index=self._chunk_index,
            )
            return []

        # Safe — release the hold.
        self._hold_buffer = ""
        self._released.append(hold)
        return list(hold)

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------

    def _scan_for_patterns(self) -> Optional[str]:
        """Scan the tail of scan_buffer for hard_never literals.

        Only scans the last ``scan_window`` characters to keep per-chunk
        cost bounded (O(scan_window + matches) for AC, not O(total)).

        Returns the matched literal string, or None if clean.
        """
        # Trim scan_buffer to the scan window
        if len(self._scan_buffer) > self._scan_window:
            self._scan_buffer = self._scan_buffer[-self._scan_window:]

        tail = self._scan_buffer

        # AC fast path
        if self._ac is not None:
            for _end_idx, (_, literal) in self._ac.iter(tail):
                return literal
            return None

        # O(n*m) fallback path
        for literal in self._hard_never_literals:
            if literal in tail:
                return literal
        return None

    def _release_aged(self) -> list[str]:
        """Move characters that have aged past hold_window from hold to released.

        Characters that are older than ``hold_window`` cannot be part of a
        not-yet-detected violation and are safe to release.
        """
        if len(self._hold_buffer) <= self._hold_window:
            return []

        release_count = len(self._hold_buffer) - self._hold_window
        to_release = self._hold_buffer[:release_count]
        self._hold_buffer = self._hold_buffer[release_count:]
        self._released.append(to_release)
        return list(to_release)

    # ----------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------

    def reset(self) -> None:
        """Reset all per-turn state for the next streaming call.

        The automaton and window sizes are preserved (they are per-character,
        not per-turn).
        """
        self._scan_buffer = ""
        self._hold_buffer = ""
        self._released = []
        self._chunk_index = 0
        self._total_chars_received = 0
        self._halted = False
        self._halt_info = None


# ============================================================
# Convenience
# ============================================================


def build_prefilter_from_soul(
    soul: dict[str, Any],
    *,
    hold_window: int = _MIN_HOLD_WINDOW,
) -> StreamingPreFilter:
    """One-shot: build a StreamingPreFilter from a raw soul spec dict.

    Args:
        soul: Soul spec dict with an ``anti_patterns`` key.
        hold_window: Characters to hold before releasing.

    Returns:
        A ready-to-use StreamingPreFilter.
    """
    sync = AntiPatternFilter(soul)
    return StreamingPreFilter.from_sync_filter(sync, hold_window=hold_window)
