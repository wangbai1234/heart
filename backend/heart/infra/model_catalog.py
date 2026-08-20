"""Authoritative user-selectable LLM catalog for yuoyuo.

Public slugs are stable product identifiers. MICU model IDs and credentials stay
server-side so clients cannot bypass pricing or bind themselves to relay details.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    family: str
    tags: tuple[str, str]
    description: str
    cost_coins: float
    protocol: str
    api_model: str
    credential_group: str
    failover: tuple[str, ...]

    def public_dict(self) -> dict:
        value = asdict(self)
        value.pop("protocol")
        value.pop("api_model")
        value.pop("credential_group")
        value["tags"] = list(self.tags)
        value["failover"] = list(self.failover)
        return value


DEFAULT_CHAT_MODEL = "gemini-3.1"

MODEL_CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        "gemini-3.1",
        "Gemini 3.1",
        "Gemini",
        ("🚗高手", "粘人小狗"),
        "氛围一到就贴上来，甜和野都接得住",
        0.5,
        "chat_completions",
        "gemini-3.1",
        "gemini",
        ("claude-haiku-4.5",),
    ),
    ModelSpec(
        "deepseek-v4-flash",
        "DeepSeek V4 Flash",
        "DeepSeek",
        ("嘴快小狗", "秒接梗"),
        "回复利落，适合轻松日常和快速斗嘴",
        1,
        "chat_completions",
        "deepseek-v4-flash",
        "deepseek",
        ("deepseek-v4-pro", "gpt-5.5"),
    ),
    ModelSpec(
        "deepseek-v4-pro",
        "DeepSeek V4 Pro",
        "DeepSeek",
        ("高智商", "会接戏"),
        "听得懂潜台词，剧情推进更稳",
        1,
        "chat_completions",
        "deepseek-v4-pro",
        "deepseek",
        ("deepseek-v4-flash", "gpt-5.5"),
    ),
    ModelSpec(
        "claude-haiku-4.5",
        "Claude Haiku 4.5",
        "Claude",
        ("活泼小狗", "嘴甜型"),
        "轻快会夸，日常陪聊没有压力",
        0.5,
        "anthropic",
        "claude-haiku-4-5",
        "claude",
        ("gemini-3.1",),
    ),
    ModelSpec(
        "claude-sonnet-4.6",
        "Claude Sonnet 4.6",
        "Claude",
        ("细腻高手", "很会拉扯"),
        "情绪接得准，暧昧推进自然",
        2,
        "anthropic",
        "claude-sonnet-4-6",
        "claude",
        ("gpt-5.6-luna", "gpt-5.6-sol"),
    ),
    ModelSpec(
        "claude-opus-4.6",
        "Claude Opus 4.6",
        "Claude",
        ("顶级男主", "戏感拉满"),
        "强情节、高张力场面更有代入感",
        3,
        "anthropic",
        "claude-opus-4-6",
        "claude",
        ("claude-opus-5", "claude-sonnet-4.6"),
    ),
    ModelSpec(
        "claude-opus-5",
        "Claude Opus 5",
        "Claude",
        ("白月光", "后劲很大"),
        "克制深情，适合重要剧情和长线关系",
        3,
        "anthropic",
        "claude-opus-5",
        "claude",
        ("claude-opus-4.6", "claude-sonnet-4.6"),
    ),
    ModelSpec(
        "grok-4.5",
        "Grok 4.5",
        "Grok",
        ("坏嘴男友", "越怼越亲"),
        "会接挑衅，适合欢喜冤家式互动",
        1,
        "responses",
        "grok-4.5",
        "grok",
        ("grok-4.6", "gpt-5.5"),
    ),
    ModelSpec(
        "grok-4.6",
        "Grok 4.6",
        "Grok",
        ("疯批男主", "不按套路"),
        "反应出其不意，适合刺激型剧情",
        1,
        "responses",
        "grok-4.6",
        "grok",
        ("grok-4.5", "gpt-5.5"),
    ),
    ModelSpec(
        "gpt-5.6-luna",
        "GPT-5.6 Luna",
        "GPT",
        ("温柔学长", "很会哄人"),
        "稳定温柔，低落时更有陪伴感",
        2,
        "responses",
        "gpt-5.6-luna",
        "gpt",
        ("gpt-5.6-sol", "claude-sonnet-4.6"),
    ),
    ModelSpec(
        "gpt-5.5",
        "GPT-5.5",
        "GPT",
        ("全能男友", "什么都能聊"),
        "日常、剧情、情绪都均衡",
        1,
        "responses",
        "gpt-5.5",
        "gpt",
        ("deepseek-v4-pro", "grok-4.5"),
    ),
    ModelSpec(
        "gpt-5.6-sol",
        "GPT-5.6 Sol",
        "GPT",
        ("阳光小狗", "直球高手"),
        "热烈主动，不让暧昧一直卡住",
        2,
        "responses",
        "gpt-5.6-sol",
        "gpt",
        ("gpt-5.6-luna", "claude-sonnet-4.6"),
    ),
)

MODEL_BY_ID = {model.id: model for model in MODEL_CATALOG}
LEGACY_MODEL_ALIASES = {
    "deepseek": "deepseek-v4-flash",
    "deepseek-chat": "deepseek-v4-flash",
    "deepseek-reasoner": "deepseek-v4-pro",
    "grok": "grok-4.5",
}


def normalize_model_id(model_id: str | None) -> str:
    value = (model_id or DEFAULT_CHAT_MODEL).strip().lower()
    return LEGACY_MODEL_ALIASES.get(value, value)


def get_model_spec(model_id: str | None) -> ModelSpec | None:
    return MODEL_BY_ID.get(normalize_model_id(model_id))
