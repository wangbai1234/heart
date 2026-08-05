"""Layer-3 per-sentence emotion sentinels.

The composer (voice mode only) asks the LLM to prefix each dialog sentence with
a ``{E:情绪词}`` sentinel. Curly braces are chosen so the sentinel never
collides with the action-bracket families (（）/【】/[]/()) that
``stream_session._ACTION_PATTERN`` strips before TTS.

Two consumers:
  - display path (text_delta → bubble/history): sentinels must be stripped,
    tolerating a sentinel split across streaming chunk boundaries.
  - TTS path (per sentence): the sentence-head sentinel is parsed into an
    emotion label and stripped from the spoken text; the label is later mapped
    to a Fish S2 ``[中文指令]`` by the voice director.
"""

from __future__ import annotations

import re

# A complete sentinel: {E:<label>}, label = 1..8 non-brace chars.
_SENTINEL_RE = re.compile(r"\{E:([^\}]{1,8})\}")
# A prefix that could still grow into a valid sentinel (spans chunk boundary).
_PARTIAL_RE = re.compile(r"^\{E?:?[^\}]{0,8}$")
_MAX_HOLD = 12  # '{E:' + 8 label chars + '}' = 11; small slack.


def parse_sentence_emotion(sentence: str) -> tuple[str | None, str]:
    """Extract the sentence-head emotion label and strip ALL sentinels.

    Only the first sentinel counts, and only when it sits at the head (nothing
    but whitespace before it) — enforcing the "≤1 label per sentence, head
    only" rule. Stray mid-sentence sentinels are removed without effect.

    Returns ``(label_or_None, clean_text)``.
    """
    if not sentence:
        return None, sentence
    label: str | None = None
    m = _SENTINEL_RE.search(sentence)
    if m and sentence[: m.start()].strip() == "":
        label = m.group(1).strip() or None
    clean = _SENTINEL_RE.sub("", sentence)
    return label, clean


class SentinelStripper:
    """Stateful stripper for the streaming display path.

    Feed raw chunks; get back display-safe text with ``{E:...}`` removed. Holds
    a trailing partial sentinel (e.g. ``{E:轻`` before ``快}`` arrives) so a
    sentinel split across chunk boundaries never leaks a half-marker into the
    bubble. Call :meth:`flush` once the stream ends to release any final hold.
    """

    def __init__(self) -> None:
        self._hold = ""

    def feed(self, chunk: str) -> str:
        buf = self._hold + (chunk or "")
        self._hold = ""
        buf = _SENTINEL_RE.sub("", buf)
        # If a '{' tail could still grow into a sentinel, hold it back.
        idx = buf.rfind("{")
        if idx != -1:
            tail = buf[idx:]
            if len(tail) <= _MAX_HOLD and _PARTIAL_RE.match(tail):
                self._hold = tail
                buf = buf[:idx]
        return buf

    def flush(self) -> str:
        out = self._hold
        self._hold = ""
        # A dangling partial that never completed is not a real sentinel — but
        # only emit it if it doesn't look like one mid-completion. It never
        # completed, so surface it rather than swallow user-visible text.
        return out
