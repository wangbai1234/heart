"""Message splitter — turns long AI responses into short chat bubbles.

Deterministic split (no LLM): paragraph boundaries → sentence terminators →
greedy merge to stay within max_bubbles.
"""

from __future__ import annotations

import re

# Chinese/Japanese sentence terminators (kept attached to their preceding text)
_TERM_RE = re.compile(r"([。！？…]+)")


def split_response(
    text: str,
    max_chars: int = 60,
    max_bubbles: int = 4,
) -> list[str]:
    """Split *text* into at most *max_bubbles* segments.

    Strategy (in priority order):
    1. Paragraph breaks (``\\n\\n``) are hard splits.
    2. Within a paragraph > *max_chars*, split at Chinese sentence terminators
       (。！？…), keeping the terminator at the end of its segment.
    3. Any segment still > *max_chars* is left as-is (no mid-word hard chop).
    4. While ``len(segments) > max_bubbles``, merge the shortest adjacent pair.

    Returns a list of at least 1 non-empty string.
    """
    text = text.strip()
    if not text:
        return [""]

    raw = _split_into_sentences(text, max_chars)

    # Merge down to max_bubbles by repeatedly joining the shortest adjacent pair
    while len(raw) > max_bubbles:
        best = min(range(len(raw) - 1), key=lambda i: len(raw[i]) + len(raw[i + 1]))
        raw[best] = raw[best] + raw[best + 1]
        del raw[best + 1]

    return raw or [text]


def _split_into_sentences(text: str, max_chars: int) -> list[str]:
    """Break text into sentence-level segments, each ≤ max_chars where possible."""
    segments: list[str] = []

    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            segments.append(para)
            continue

        # Split by terminators; _TERM_RE.split keeps delimiters as their own items
        parts = _TERM_RE.split(para)
        buf = ""
        for part in parts:
            buf += part
            # Flush if we hit a terminator and the buffer is already substantial
            if _TERM_RE.fullmatch(part) and len(buf) >= 10:
                segments.append(buf.strip())
                buf = ""
        if buf.strip():
            segments.append(buf.strip())

    return segments if segments else [text]
