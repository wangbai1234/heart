"""Opening splitter — parse LLM output into action/text bubbles.

Segments wrapped in Chinese parentheses（）become kind='action' (grey
narration pills). Everything else becomes kind='text' (normal dialog bubble).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PAREN_RE = re.compile(r"（([^）]+)）")


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
            bubbles.append(OpeningBubble(kind="text", content=before))
        bubbles.append(OpeningBubble(kind="action", content=m.group(1).strip()))
        last_end = m.end()

    trailing = raw_text[last_end:].strip()
    if trailing:
        bubbles.append(OpeningBubble(kind="text", content=trailing))

    if not bubbles:
        bubbles.append(OpeningBubble(kind="text", content=raw_text))

    return bubbles
