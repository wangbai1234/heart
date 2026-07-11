"""Message splitter — turn a full LLM response into semantic bubble segments.

Emits a list of ``{kind, content}`` dicts:
  - ``kind='action'``: parenthetical action / expression / OOC narration.
    Rendered as a grey status bubble. Not billed. Never sent to TTS.
  - ``kind='text'``: normal dialog spoken by the character. Billed per bubble.
    Sent to TTS in voice mode.

Recognises Chinese/English/OOC brackets:
  （…）  (…)  【…】  […]

Dialog is further split at sentence terminators (。！？…!?). Adjacent text
segments shorter than ``MIN_TEXT_CHARS`` merge with the next segment so we
never emit a bubble like "嗯。".

Corner-quote brackets ``「…」`` (Japanese/Chinese dialog quoting) are treated
as protected atoms — terminators inside a `「…」` pair do not trigger a split,
so `「今晚别走。」` stays in one bubble instead of leaking `」` as an orphan.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

# Action markers: any of the paired brackets below. Contents span one line only.
_ACTION_RE = re.compile(r"[（(【\[]([^（()【\[\]）)】\n]*)[）)】\]]")

# Chinese/English sentence terminators (kept attached to the preceding text).
_TERM_RE = re.compile(r"([。！？…!?]+)")

MIN_TEXT_CHARS = 6
MAX_TEXT_BUBBLES = 6


class Segment(TypedDict):
    kind: Literal["text", "action"]
    content: str


def split_response(text: str) -> list[Segment]:
    """Split ``text`` into an ordered list of ``{kind, content}`` segments.

    Ordering is preserved: interleaved actions and dialog keep their original
    positions so the frontend can render them in one linear stream.
    """
    text = (text or "").strip()
    if not text:
        return []

    # 1. Walk the text, splitting action spans out from the dialog.
    interleaved = _split_actions_and_dialog(text)

    # 2. Break each dialog segment further by sentence terminators.
    exploded: list[Segment] = []
    for seg in interleaved:
        if seg["kind"] == "action":
            exploded.append(seg)
            continue
        for sentence in _split_by_terminators(seg["content"]):
            exploded.append({"kind": "text", "content": sentence})

    # 3. Merge tiny dialog bubbles with the next dialog bubble so we don't
    #    emit a "嗯。" solo bubble.
    merged = _merge_short_text(exploded, MIN_TEXT_CHARS)

    # 4. Cap the number of text bubbles by folding the smallest adjacent
    #    text pair together.
    return _cap_text_bubbles(merged, MAX_TEXT_BUBBLES)


def _split_actions_and_dialog(text: str) -> list[Segment]:
    """Extract action spans and keep everything else as text (unchunked)."""
    out: list[Segment] = []
    cursor = 0
    for m in _ACTION_RE.finditer(text):
        pre = text[cursor : m.start()].strip()
        if pre:
            out.append({"kind": "text", "content": pre})
        inner = m.group(1).strip()
        if inner:
            out.append({"kind": "action", "content": inner})
        cursor = m.end()
    tail = text[cursor:].strip()
    if tail:
        out.append({"kind": "text", "content": tail})
    return out


def _split_by_terminators(text: str) -> list[str]:
    """Split a dialog run at terminators, keeping each terminator attached.

    Terminators (`。！？…!?`) that appear *inside* a ``「…」`` pair are treated
    as part of the quoted content and do not trigger a split — otherwise the
    closing `」` leaks into its own orphan bubble.
    """
    parts = _TERM_RE.split(text)
    out: list[str] = []
    buf = ""
    corner_quote_depth = 0
    for part in parts:
        if not _TERM_RE.fullmatch(part):
            corner_quote_depth += part.count("「") - part.count("」")
            if corner_quote_depth < 0:
                corner_quote_depth = 0
        buf += part
        if _TERM_RE.fullmatch(part) and corner_quote_depth == 0:
            stripped = buf.strip()
            if stripped:
                out.append(stripped)
            buf = ""
    stripped = buf.strip()
    if stripped:
        out.append(stripped)
    return out or [text.strip()]


def _merge_short_text(segments: list[Segment], min_chars: int) -> list[Segment]:
    """Merge short text with the IMMEDIATELY-following text segment.

    Only merges if the next segment is also text (no action in between), so
    reading order and action placement are preserved. A short text followed
    by an action is kept as its own bubble even if under the threshold —
    reordering around an action would confuse the reader.
    """
    result: list[Segment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["kind"] == "text"
            and len(seg["content"]) < min_chars
            and i + 1 < len(segments)
            and segments[i + 1]["kind"] == "text"
        ):
            merged = seg["content"] + segments[i + 1]["content"]
            result.append({"kind": "text", "content": merged})
            i += 2
            continue
        result.append(seg)
        i += 1
    return result


def _cap_text_bubbles(segments: list[Segment], max_bubbles: int) -> list[Segment]:
    """Ensure at most max_bubbles text segments by folding smallest adjacent."""
    text_indices = [i for i, s in enumerate(segments) if s["kind"] == "text"]
    while len(text_indices) > max_bubbles:
        # Find the smallest adjacent text pair (adjacent by text index, may
        # have actions between them in the segments list).
        best_i = min(
            range(len(text_indices) - 1),
            key=lambda k: (
                len(segments[text_indices[k]]["content"])
                + len(segments[text_indices[k + 1]]["content"])
            ),
        )
        a = text_indices[best_i]
        b = text_indices[best_i + 1]
        # Merge b into a, preserving action segments that sit between them.
        segments[a] = {"kind": "text", "content": segments[a]["content"] + segments[b]["content"]}
        segments.pop(b)
        text_indices = [i for i, s in enumerate(segments) if s["kind"] == "text"]
    return segments
