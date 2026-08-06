"""Sentence Splitter — stream token splitter for TTS."""

from __future__ import annotations

from typing import List


class SentenceSplitter:
    """Stream splitter: accumulate tokens, split at sentence boundaries.

    Bracket-aware: never splits while inside a （）/()/【】 action span. The TTS
    path strips those spans (stream_session._ACTION_PATTERN) but only when the
    brackets stay PAIRED within one sentence. Splitting on a terminator or
    MAX_LEN mid-bracket (e.g. ``（她停顿了一下。目光落向别处）``) would leave an
    unpaired bracket in each half → the strip regex can't match → the bracketed
    stage direction gets read aloud. So we hold the split until brackets close.
    A HARD_MAX ceiling bounds a never-closed bracket so the buffer can't grow
    unbounded on malformed model output.
    """

    TERMINATORS = "。！？!?;；…"
    OPENERS = "（(【"
    CLOSERS = "）)】"
    MIN_LEN = 6  # Don't split too short (avoid single-char TTS)
    MAX_LEN = 50  # Prefer to split by here (only when brackets are balanced)
    HARD_MAX = 160  # Absolute ceiling — force split even mid-bracket

    def __init__(self):
        self._buf: List[str] = []
        self._len = 0
        self._depth = 0  # open-bracket depth; >0 means inside a （）/【】 span

    def feed(self, delta: str) -> List[str]:
        """Feed token delta, return list of complete sentences (may be empty)."""
        out = []
        for ch in delta:
            self._buf.append(ch)
            self._len += 1
            if ch in self.OPENERS:
                self._depth += 1
            elif ch in self.CLOSERS and self._depth > 0:
                self._depth -= 1
            # A natural split (terminator or soft MAX_LEN) is only safe outside a
            # bracket span; otherwise keep buffering until the bracket closes, up
            # to the HARD_MAX backstop.
            balanced = self._depth == 0
            natural = balanced and (
                (ch in self.TERMINATORS and self._len >= self.MIN_LEN) or self._len >= self.MAX_LEN
            )
            if natural or self._len >= self.HARD_MAX:
                out.append("".join(self._buf))
                self._buf = []
                self._len = 0
                self._depth = 0
        return out

    def flush(self) -> str | None:
        """Flush remaining buffer as a sentence."""
        if self._buf:
            s = "".join(self._buf)
            self._buf = []
            self._len = 0
            self._depth = 0
            return s
        return None
