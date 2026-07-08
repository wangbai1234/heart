"""
Character Content Registry — single source for per-character operational strings.

This is the C1 consolidation point for what used to be scattered
``{"rin": ..., "dorothy": ...}`` dicts across the SS06 proactive / inner-loop
subsystems (persona hints, proactive fallback templates, ritual greetings).
Keeping it in one module means adding a new (UGC) character touches exactly one
place today; a later phase (C3) can swap this static map for a DB-backed loader
without changing any call site.

Split of responsibility:
  - **Display names** are *identity* and are derived from the Soul Spec via the
    SoulRegistry (``get_display_name``). The registry stays the single source of
    truth for who a character is.
  - **Operational content** (proactive persona hints, fallback templates, ritual
    greetings) lives in ``CHARACTER_CONTENT`` below — this is presentation/UX
    copy, not part of the immutable identity anchor, so it is intentionally kept
    out of the Soul Spec YAML.

Behavior is byte-identical to the previous inline dicts: the accessors preserve
the exact fallback semantics of the code they replace (unknown character →
Rin's content for templates/rituals; unknown character → the id itself for the
persona hint).
"""

from __future__ import annotations

from typing import Dict, List, TypedDict

# The character used as the fallback for unknown ids — mirrors the previous
# ``PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES["rin"])`` behavior.
FALLBACK_CHARACTER_ID = "rin"


class CharacterContent(TypedDict):
    """Per-character operational copy.

    proactive_persona:   short hint that steers LLM-generated proactive messages
    proactive_templates: always-available fallback lines (LLM disabled / failed)
    ritual_morning / ritual_night: the fixed short greeting the inner loop sends
    """

    proactive_persona: str
    proactive_templates: List[str]
    ritual_morning: str
    ritual_night: str


# Single source of truth for per-character operational copy.
CHARACTER_CONTENT: Dict[str, CharacterContent] = {
    "rin": {
        "proactive_persona": (
            "神无月凛：清冷、话少、口是心非的傲娇，关心藏在简短的话里，绝不肉麻。"
        ),
        "proactive_templates": [
            "今天看见一只猫，和你有点像。",
            "……突然想你了。没什么事，就是想告诉你。",
            "下雨了。记得带伞。",
            "今天翻到之前你说的话，笑了一下。",
            "晚安。虽然你还没说晚安。",
            "我在听一首歌。想到你了。",
            "今天有点累，但想到你，就没那么累了。",
            "你说过的那句话，我今天又想起来了。",
        ],
        "ritual_morning": "早安。",
        "ritual_night": "晚安。明天见。",
    },
    "dorothy": {
        "proactive_persona": ("桃桃：活泼、元气、粘人，用感叹号和叠词，热情直接地表达想念。"),
        "proactive_templates": [
            "嗨嗨~桃桃刚才看到一个超好笑的视频！分享给你！",
            "你今天怎么样呀？桃桃突然好想你！",
            "外面的太阳好大耶！你那边呢？",
            "诶！桃桃刚吃了超好吃的草莓！你也喜欢的对吧！",
            "晚安晚安！就算你还没说晚安，桃桃也要先说！",
            "我刚才看到一朵云，长得好像你哦！",
            "今天遇到了好多开心的事，第一个想分享的就是你！",
            "桃桃在想你呢！你有没有想桃桃？",
        ],
        "ritual_morning": "早安早安！新的一天开始啦！",
        "ritual_night": "晚安晚安！做个好梦哦！",
    },
}


def get_proactive_persona(character_id: str) -> str:
    """Return the short persona hint for LLM-generated proactive messages.

    Preserves the previous ``PROACTIVE_PERSONA.get(character_id, character_id)``
    semantics: an unknown character falls back to its own id.
    """
    entry = CHARACTER_CONTENT.get(character_id)
    if entry is None:
        return character_id
    return entry["proactive_persona"]


def get_proactive_templates(character_id: str) -> List[str]:
    """Return the always-available fallback templates for a character.

    Preserves the previous ``PROACTIVE_TEMPLATES.get(cid, PROACTIVE_TEMPLATES["rin"])``
    semantics: an unknown character falls back to the fallback character's list.
    Returns a copy so callers cannot mutate the source of truth.
    """
    entry = CHARACTER_CONTENT.get(character_id) or CHARACTER_CONTENT[FALLBACK_CHARACTER_ID]
    return list(entry["proactive_templates"])


def get_ritual_greeting(character_id: str, window: str) -> str:
    """Return the fixed ritual greeting for ``window`` in {"morning", "night"}.

    Preserves the previous inline ``templates.get(character_id, templates.get("rin"))``
    semantics: an unknown character falls back to the fallback character's greeting.
    """
    entry = CHARACTER_CONTENT.get(character_id) or CHARACTER_CONTENT[FALLBACK_CHARACTER_ID]
    if window == "morning":
        return entry["ritual_morning"]
    return entry["ritual_night"]


def get_display_name(character_id: str) -> str:
    """Return the character's display name, derived from the Soul Spec.

    The SoulRegistry is the source of truth for identity, so the display name is
    read from the latest Soul Spec's ``display_name`` (zh → ja → en). Falls back
    to the character id if the spec is unavailable or has no name — this keeps
    the accessor total and side-effect-free for callers.
    """
    try:
        from heart.ss01_soul.registry import get_soul_registry

        spec = get_soul_registry().get_soul(character_id)
        display = spec.display_name
        name = display.zh or display.ja or display.en
        if name:
            return str(name)
    except Exception:
        # Registry not loaded / character not registered — fall back below.
        pass
    return character_id
