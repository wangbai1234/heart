"""Sentence Splitter — stream token splitter for TTS."""

from __future__ import annotations

from typing import List


class SentenceSplitter:
    """Stream splitter: accumulate tokens, split at sentence boundaries."""

    TERMINATORS = "。！？!?;；…"
    MIN_LEN = 6  # Don't split too short (avoid single-char TTS)
    MAX_LEN = 50  # Force split if too long

    def __init__(self):
        self._buf: List[str] = []
        self._len = 0

    def feed(self, delta: str) -> List[str]:
        """Feed token delta, return list of complete sentences (may be empty)."""
        out = []
        for ch in delta:
            self._buf.append(ch)
            self._len += 1
            if (ch in self.TERMINATORS and self._len >= self.MIN_LEN) or self._len >= self.MAX_LEN:
                out.append("".join(self._buf))
                self._buf = []
                self._len = 0
        return out

    def flush(self) -> str | None:
        """Flush remaining buffer as a sentence."""
        if self._buf:
            s = "".join(self._buf)
            self._buf = []
            self._len = 0
            return s
        return None
