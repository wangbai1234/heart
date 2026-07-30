"""Opening prompt templates — build_opening_prompt function."""

from __future__ import annotations

from .prompt import DEFAULT_STYLE, STYLE_DIRECTIVES


def build_opening_prompt(
    *,
    display_name: str,
    persona: str,
    backstory: str | None = None,
    tags: list[str] | None = None,
    greeting_style: str = DEFAULT_STYLE,
) -> list[dict[str, str]]:
    """Build the messages list for the opening scene LLM call.

    Returns a standard [{"role": ..., "content": ...}] list ready for
    ModelRouter.call_cheap().
    """
    style = STYLE_DIRECTIVES.get(greeting_style, STYLE_DIRECTIVES[DEFAULT_STYLE])

    background_section = _build_background(persona, backstory, tags)

    system_prompt = (
        f"你是{display_name}。\n"
        f"{persona[:300]}\n\n"
        f"【背景信息】\n{background_section}\n\n"
        "【开场生成指令】\n"
        "你正在与一个人第一次相遇。"
        "请生成一段沉浸式的初遇开场。\n\n"
        "严格按以下结构输出：\n"
        "1. 用（）括起场景描述："
        "1-2句，写出此刻的时间、"
        "地点和氛围。要有画面感。\n"
        "2. 用（）括起角色动作："
        "1句，描写你此刻的动作或"
        "神态，体现性格。\n"
        "3. 第一句对白：以你的语气"
        "自然说出。要体现身份、"
        "性格，制造关系张力。\n"
        "4. 结尾留出互动空间：问句、"
        "眼神邀约、或动作暗示，"
        "让对方想要回应。\n\n"
        f"【语气风格】{style['tone']}\n"
        f"【场景氛围】{style['atmosphere']}\n"
        f"【情绪目标】{style['emotion_goal']}\n\n"
        "【禁止】\n"
        "- 禁止自我介绍（例如你好"
        "我是谁谁谁）\n"
        "- 禁止普通寒暄（例如很高兴"
        "认识你）\n"
        "- 禁止客服式欢迎\n"
        "- 禁止编造角色不存在的经历"
        "（前任、童年秘密等）\n"
        "- 禁止使用引号包裹对白\n\n"
        "【输出格式】\n"
        "- 场景和动作用中文括号"
        "（）包裹，各占一行\n"
        "- 对白直接输出，不加引号\n"
        "- 总长度150-300字\n"
        "- 不要输出编号或标签"
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
