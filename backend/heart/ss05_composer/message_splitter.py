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

# Action markers: any of the paired brackets below. Content may span multiple
# lines — DeepSeek sometimes wraps long action prose with a newline before the
# closing `）`, and excluding `\n` from the negated class caused the closing
# bracket to leak into its own text bubble (TEST_REPORT_20260712 follow-up:
# `（指尖轻抬，...嘲讽\n急着走？）俯身...` split into two orphan text bubbles).
_ACTION_RE = re.compile(r"[（(【\[]([^（()【\[\]）)】]*)[）)】\]]")

# Chinese/English sentence terminators (kept attached to the preceding text).
_TERM_RE = re.compile(r"([。！？…!?]+)")

MIN_TEXT_CHARS = 6
MAX_TEXT_BUBBLES = 6


# ── Post-hoc action bracketing (Plan B for TEST_REPORT_20260712) ──────────────
#
# When the LLM ignores the "wrap actions in （）" contract in the system prompt
# (see composer.service._build_system_prompt Layer 3.5) we still have to render
# something reasonable. This heuristic detects action prose that begins with a
# body-part / expression / voice noun and inserts brackets around it so the
# splitter treats it as ``kind='action'``.
#
# Scope is deliberately narrow — false positives read as "wrong bubble color",
# which is worse than missing a wrap. Only wraps segments that both:
#  1. Start with an ACTION_SUBJECT noun (目光, 神情, 声音, …), and
#  2. Are followed by either (a) end-of-segment, or (b) a whitespace boundary
#     with a common DIALOG_STARTER after it (不, 我, 你, 嗯, …).
_ACTION_SUBJECTS_LIST: tuple[str, ...] = (
    # 身体
    "目光",
    "视线",
    "眼神",
    "眼底",
    "眼中",
    "眉",
    "眉头",
    "眉眼",
    "双眉",
    "唇",
    "嘴角",
    "嘴唇",
    "指尖",
    "指腹",
    "手指",
    "双手",
    "脸",
    "脸颊",
    "脸色",
    "下颌",
    "睫毛",
    "眼睫",
    "睫",
    # 状态
    "神情",
    "神色",
    "表情",
    "气息",
    "气场",
    "姿势",
    "神态",
    "呼吸",
    # 语音
    "声音",
    "语气",
    "语调",
    "音色",
    "嗓音",
    "语速",
    # 心境
    "心跳",
    "心口",
)
# Pattern is intentionally UNANCHORED so `.search()` can find a subject noun
# anywhere in the segment (needed for the "转身，目光带着审视 你..." case
# where the segment starts with a plain verb and the subject shows up mid-
# string). `.match()` still works — Python's re.match anchors implicitly to
# the start regardless of whether the pattern has a leading `^`.
_ACTION_SUBJECT_RE = re.compile(r"(?:" + "|".join(_ACTION_SUBJECTS_LIST) + r")")

# Words that commonly start a spoken utterance in Chinese. We use these to
# confirm that the whitespace we found in a segment is really the seam between
# an action span and a dialog span, not incidental whitespace inside prose.
_DIALOG_STARTERS_LIST: tuple[str, ...] = (
    "不",
    "是",
    "好",
    "嗯",
    "哦",
    "哎",
    "那",
    "这",
    "我",
    "你",
    "他",
    "她",
    "它",
    "只",
    "也",
    "但",
    "可",
    "就",
    "要",
    "会",
    "有",
    "没",
    "说",
    "让",
    "真",
    "其实",
    "因为",
    "所以",
    "如果",
    "等等",
    "来",
    "去",
    "一",
    "又",
    "再",
    "已",
    "向",
    "从",
    "对",
    "把",
    "被",
    "将",
    "想",
    "该",
    "能",
    "敢",
    "吧",
    "呢",
    "啊",
    "呀",
    "吗",
    "嘛",
)
_DIALOG_START_RE = re.compile(r"(?:" + "|".join(_DIALOG_STARTERS_LIST) + r")")


def _wrap_bare_actions(text: str) -> str:
    """Wrap action-prose segments that the LLM forgot to bracket.

    Operates on terminator-split pieces; segments that already contain any
    action bracket are left untouched so we never double-wrap. See module
    docstring for the two-part rule.
    """
    if not text:
        return text
    # If the LLM used ANY explicit bracket in this reply, assume it followed
    # the format contract and don't second-guess it — keeps the heuristic
    # well away from correctly-formatted turns.
    if any(marker in text for marker in ("（", "(", "【", "[")):
        return text

    parts = _TERM_RE.split(text)
    out: list[str] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if _TERM_RE.fullmatch(part):
            out.append(part)
            i += 1
            continue
        stripped = part.strip()
        # Gate: use `search` (not `match`) so cases where the action subject
        # sits mid-string still qualify — e.g. "转身，目光带着审视 你..."
        # where the segment starts with a non-subject verb ("转身") but the
        # subject noun ("目光") shows up after a comma. The seam checks below
        # keep this from over-triggering on plain dialog that happens to
        # mention body parts ("你今天的目光很温柔").
        if not stripped or not _ACTION_SUBJECT_RE.search(stripped):
            out.append(part)
            i += 1
            continue

        # Preserve leading whitespace so recombination round-trips exactly.
        leading = part[: len(part) - len(part.lstrip())]
        trailing = part[len(part.rstrip()) :]
        body = stripped

        # Case A: body has a whitespace seam whose right side starts with a
        # dialog-starter word — split there, wrap the left side. Require the
        # action side (pre-seam) to actually contain a subject noun; otherwise
        # the subject lives inside the dialog half and this isn't action
        # prose we should wrap.
        seam_match = re.search(rf"(.*?)\s+({_DIALOG_START_RE.pattern}.*)$", body)
        if seam_match:
            action, dialog = seam_match.group(1).rstrip(), seam_match.group(2).lstrip()
            if action and _ACTION_SUBJECT_RE.search(action):
                out.append(f"{leading}（{action}）{dialog}{trailing}")
                i += 1
                continue

        # Case B: no obvious seam — wrap the whole segment ONLY when it
        # actually starts with a subject noun. When the subject sits mid-
        # string with no seam ("我说话不错。目光很好看。") we leave it as
        # dialog. Absorb the trailing terminator inside the bracket so a lone
        # `。` doesn't leak into an empty text bubble after the action pill.
        if not _ACTION_SUBJECT_RE.match(stripped):
            out.append(part)
            i += 1
            continue
        next_term = ""
        if i + 1 < len(parts) and _TERM_RE.fullmatch(parts[i + 1]):
            next_term = parts[i + 1]
            i += 2
        else:
            i += 1
        out.append(f"{leading}（{body}{next_term}）{trailing}")

    return "".join(out)


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

    # 0. Pre-process: if the LLM emitted an action-prose seam without brackets,
    #    wrap it now so the downstream splitter can recognise it as an action.
    text = _wrap_bare_actions(text)

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
    """Extract action spans and keep everything else as text (unchunked).

    Both action pills and text bubbles collapse interior whitespace runs to
    a single space. Frontend renders bubbles with ``whitespace-pre-wrap``,
    so any ``\\n`` the LLM inserts as its own formatting would otherwise
    show as a blank line inside the bubble ("同气泡空行" report).
    """
    out: list[Segment] = []
    cursor = 0
    for m in _ACTION_RE.finditer(text):
        pre = re.sub(r"\s+", " ", text[cursor : m.start()]).strip()
        if pre:
            out.append({"kind": "text", "content": pre})
        inner = re.sub(r"\s+", " ", m.group(1)).strip()
        if inner:
            out.append({"kind": "action", "content": inner})
        cursor = m.end()
    tail = re.sub(r"\s+", " ", text[cursor:]).strip()
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
