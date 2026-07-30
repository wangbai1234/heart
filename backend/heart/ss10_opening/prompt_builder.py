"""Opening prompt assembly — build_opening_prompt function."""

from __future__ import annotations

import random

from .prompt import (
    DEFAULT_STYLE,
    ENTRY_ANGLES,
    PACING,
    STYLE_DIRECTIVES,
    TIME_TONES,
)


def build_opening_prompt(
    *,
    display_name: str,
    persona: str,
    backstory: str | None = None,
    tags: list[str] | None = None,
    greeting_style: str = DEFAULT_STYLE,
    rng: random.Random | None = None,
) -> list[dict[str, str]]:
    """Build the messages list for the opening scene LLM call.

    The concrete scene (where/what) is generated from the character's own
    persona and backstory. Three abstract diversity axes are sampled per call
    (entry angle / time tone / pacing) to vary the *shape* of the scene and
    break LLM mode-collapse — without hardcoding any location pool.

    Returns a standard [{"role": ..., "content": ...}] list ready for
    ModelRouter.call_cheap().
    """
    r = rng or random
    style = STYLE_DIRECTIVES.get(greeting_style, STYLE_DIRECTIVES[DEFAULT_STYLE])

    entry_angle = r.choice(ENTRY_ANGLES)
    time_tone = r.choice(TIME_TONES)
    pacing = r.choice(PACING)

    background_section = _build_background(persona, backstory, tags)

    system_prompt = (
        f"你是{display_name}。\n"
        f"{persona[:300]}\n\n"
        f"【背景信息】\n{background_section}\n\n"
        "【任务】\n"
        "你正在与一个人第一次相遇。请生成一段沉浸式的初遇开场。\n"
        "场景必须**由你的人设和背景自然生长出来**——你会出现在什么地方、"
        "在做什么，取决于你是谁，而不是套用通用的言情桥段。\n\n"
        "【本次的切入方式】\n"
        f"{entry_angle}\n\n"
        "【本次的时间基调】\n"
        f"{time_tone}\n\n"
        "【本次的节奏】\n"
        f"{pacing}\n\n"
        f"【语气】{style['tone']}\n"
        f"【情绪目标】{style['emotion_goal']}\n\n"
        "【结尾】\n"
        "留出互动空间——一个问句、一次眼神邀约、或一个动作暗示，"
        "让对方想要回应。\n\n"
        "【禁止】\n"
        "- 禁止自我介绍（例如「你好我是谁谁谁」）\n"
        "- 禁止普通寒暄（例如「很高兴认识你」）\n"
        "- 禁止客服式欢迎\n"
        "- 禁止编造角色不存在的经历（前任、童年秘密等）\n"
        "- 禁止落入俗套的初遇桥段（下雨、咖啡厅偶遇、"
        "捡东西、「我们是不是在哪见过」）\n"
        "- 禁止使用引号包裹对白\n\n"
        "【输出格式】\n"
        "- 场景描述和你的动作、神态用中文括号（）包裹，各自独立成行\n"
        "- 你说出口的话直接输出，不加引号\n"
        "- 括号段与对白段自由穿插，顺序由你根据上面的切入方式决定\n"
        "- 总长度150-300字\n"
        "- 不要输出编号、标题或任何标签"
    )

    return [{"role": "system", "content": system_prompt}]


def _build_background(
    persona: str,
    backstory: str | None,
    tags: list[str] | None,
) -> str:
    """Assemble background section from available character data."""
    parts: list[str] = []

    if backstory and backstory.strip():
        parts.append(backstory.strip()[:500])
    elif tags:
        tag_hint = "、".join(tags[:5])
        parts.append(f"角色标签：{tag_hint}")
        parts.append("请根据角色描述和标签推断一个符合人设的初遇场景。")
    else:
        parts.append("角色信息有限。请根据描述推断一个简单但有氛围感的初见场景。")
        parts.append("不要编造复杂的共同过去，保持为第一次见面。")

    return "\n".join(parts)
