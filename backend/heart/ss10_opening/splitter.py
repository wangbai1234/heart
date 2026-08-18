"""Opening splitter — parse LLM output into action/text bubbles.

Segments wrapped in Chinese parentheses（）become kind='action' (grey
narration pills). Everything else becomes kind='text' (normal dialog bubble).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PAREN_RE = re.compile(r"（([^）]+)）")

# Users often wrap dialogue in double quotes out of prose habit. The chat bubble
# already signals "this is speech", so an outer pair is redundant. Strip it —
# but only when the WHOLE segment is one wrapped span and the quote char never
# recurs inside (so genuine inner quotations survive untouched). Conservative by
# design: an unbalanced or partial quote is left exactly as written.
_QUOTE_PAIRS = (("“", "”"), ('"', '"'))


def _strip_wrapping_quotes(text: str) -> str:
    for open_q, close_q in _QUOTE_PAIRS:
        if len(text) >= 2 and text.startswith(open_q) and text.endswith(close_q):
            inner = text[len(open_q) : len(text) - len(close_q)]
            # No recurrence of either quote char inside → safe to unwrap.
            if open_q not in inner and close_q not in inner:
                return inner.strip()
    return text


@dataclass
class OpeningBubble:
    kind: str  # 'action' | 'text'
    content: str


def split_opening(raw_text: str) -> list[OpeningBubble]:
    """Split raw LLM output into ordered action/text segments."""
    raw_text = raw_text.strip()
    if not raw_text:
        return []

    bubbles: list[OpeningBubble] = []
    last_end = 0

    for m in _PAREN_RE.finditer(raw_text):
        before = raw_text[last_end : m.start()].strip()
        if before:
            bubbles.append(OpeningBubble(kind="text", content=_strip_wrapping_quotes(before)))
        bubbles.append(OpeningBubble(kind="action", content=m.group(1).strip()))
        last_end = m.end()

    trailing = raw_text[last_end:].strip()
    if trailing:
        bubbles.append(OpeningBubble(kind="text", content=_strip_wrapping_quotes(trailing)))

    if not bubbles:
        bubbles.append(OpeningBubble(kind="text", content=_strip_wrapping_quotes(raw_text)))

    return bubbles
