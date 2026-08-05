"""Layer-3 voice instruction markup — display-path stripping.

In voice turns the composer asks the LLM to prefix spoken sentences with a
natural-language Fish S2 instruction in half-width square brackets, e.g.
``[温柔地说]今天累不累？``. Those ``[...]`` spans are the *instruction*
namespace: they must reach Fish (TTS path keeps them raw) but must never show
up in the chat bubble or history (display path strips them). Actions/narration
use the full-width ``（）`` / ``【】`` namespace instead and are handled by
``stream_session._ACTION_PATTERN``.

This module only owns the display side: strip complete ``[...]`` spans from the
streamed text_delta, tolerating a span split across chunk boundaries.
"""

from __future__ import annotations

import re

# A complete instruction span: [ ... ] with no nested bracket or newline.
_INSTR_RE = re.compile(r"\[[^\[\]\n]*\]")
# Longest partial '[...' we'll hold waiting for the closing ']'. Fish
# instructions are short natural-language phrases; 40 chars is ample slack.
_MAX_HOLD = 40


class InstructionStripper:
    """Stateful stripper for the streaming display path.

    Feed raw chunks; get back display-safe text with ``[...]`` instruction
    spans removed. Holds a trailing partial span (e.g. ``[温柔`` before ``地说]``
    arrives) so a span split across chunk boundaries never leaks a half-marker
    into the bubble. Call :meth:`flush` once the stream ends to release any
    final hold (a ``[`` that never closed is surfaced, not swallowed).
    """

    def __init__(self) -> None:
        self._hold = ""

    def feed(self, chunk: str) -> str:
        buf = self._hold + (chunk or "")
        self._hold = ""
        buf = _INSTR_RE.sub("", buf)
        # If an unclosed '[' tail could still grow into a span, hold it back.
        idx = buf.rfind("[")
        if idx != -1 and "]" not in buf[idx:]:
            tail = buf[idx:]
            if len(tail) <= _MAX_HOLD and "\n" not in tail:
                self._hold = tail
                buf = buf[:idx]
        return buf

    def flush(self) -> str:
        out = self._hold
        self._hold = ""
        return out
