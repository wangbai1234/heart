"""
SS05 Composer - 示例使用 Model Router

展示如何在实际代码中调用 LLM 模型
"""

from typing import AsyncGenerator
from heart.infra.llm import get_model_router

# ============================================================================
# 示例 1: 主响应 (SS05 - Composer)
# 用于: 生成角色的主要回应
# 模型: deepseek-reasoner (高质量)
# ============================================================================


async def generate_response(
    user_message: str,
    character_context: str,
    conversation_history: list[dict],
) -> str:
    """
    生成角色响应 (同步模式)

    Args:
        user_message: 用户消息
        character_context: 角色背景设定
        conversation_history: 对话历史

    Returns:
        角色的响应文本
    """
    router = await get_model_router()

    messages = [
        {
            "role": "system",
            "content": f"You are {character_context}. Respond naturally and authentically.",
        },
        *conversation_history,
        {"role": "user", "content": user_message},
    ]

    # 调用主模型 - 会自动使用 deepseek-reasoner
    response = await router.call_main(
        messages=messages,
        temperature=0.7,  # 适度创意
        max_tokens=2000,
        agent_name="Composer.generate_response",
    )

    return response


async def stream_response(
    user_message: str,
    character_context: str,
    conversation_history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    流式生成角色响应 (流式模式)

    用于前端实时显示 token 流，提供更好的用户体验

    Yields:
        响应文本的片段
    """
    router = await get_model_router()

    messages = [
        {
            "role": "system",
            "content": f"You are {character_context}. Respond naturally and authentically.",
        },
        *conversation_history,
        {"role": "user", "content": user_message},
    ]

    # 调用主模型（流式）
    async for chunk in router.stream_main(
        messages=messages,
        temperature=0.7,
        max_tokens=2000,
        agent_name="Composer.stream_response",
    ):
        yield chunk


# ============================================================================
# 示例 2: 便宜操作 (SS02 Memory - 记忆编码)
# 用于: 编码对话内容为记忆向量
# 模型: deepseek-chat (便宜快速)
# ============================================================================


async def encode_memory_entry(
    conversation_text: str,
    user_id: str,
) -> dict:
    """
    将对话编码为结构化记忆条目

    Args:
        conversation_text: 要编码的对话文本
        user_id: 用户 ID

    Returns:
        结构化的记忆条目
    """
    router = await get_model_router()

    messages = [
        {
            "role": "system",
            "content": """You are a memory encoder. Extract and structure conversation information.
            Return valid JSON with fields: summary, entities, emotions, topics.""",
        },
        {"role": "user", "content": conversation_text},
    ]

    # 调用便宜模型，强制 JSON 输出
    response = await router.call_cheap(
        messages=messages,
        temperature=0.1,  # 低温度保证一致的输出
        max_tokens=1000,
        json_mode=True,  # 强制 JSON 格式
        agent_name="Memory.encode_entry",
    )

    import json
    return json.loads(response)


# ============================================================================
# 示例 3: 便宜操作 (SS07 Safety - 安全分类)
# 用于: 检测不安全内容
# 模型: deepseek-chat (便宜快速)
# ============================================================================


async def safety_check(message: str) -> dict:
    """
    安全性检查（是否包含有害内容）

    Args:
        message: 要检查的消息

    Returns:
        安全性评分和分类
    """
    router = await get_model_router()

    messages = [
        {
            "role": "system",
            "content": """You are a safety classifier. Analyze if the message contains:
            - Harmful content
            - Personal information leaks
            - Unsafe requests
            Return JSON: {is_safe: bool, risk_level: 'low'|'medium'|'high', reason: str}""",
        },
        {"role": "user", "content": message},
    ]

    response = await router.call_cheap(
        messages=messages,
        temperature=0.1,
        max_tokens=500,
        json_mode=True,
        agent_name="Safety.check",
    )

    import json
    return json.loads(response)


# ============================================================================
# 核心要点总结
# ============================================================================

"""
✅ 所有 LLM 调用必须通过 Model Router:
   - ❌ 不要直接导入 OpenAI/Anthropic SDK
   - ✅ 只调用 get_model_router() -> call_main() / call_cheap()

✅ 两层模型选择:
   - main: deepseek-reasoner    → 高质量响应 (SS05 Composer)
   - cheap: deepseek-chat        → 快速低成本 (SS02/03/07)

✅ 调用参数:
   - agent_name: 标记调用来源（用于日志和监控）
   - json_mode: 强制 JSON 输出（用于结构化数据）
   - temperature: 低值(0.1)用于分类，高值(0.7)用于创意

✅ 成本优化:
   - 编码、分类、检查 → call_cheap()
   - 主响应、创意写作 → call_main()
   - 避免不必要的大模型调用

✅ 后续迁移到其他模型很容易:
   只需改 config.py，无需修改所有 subsystem 的代码
"""
