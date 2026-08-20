"""Authoritative user-selectable LLM product catalog for yuoyuo.

Public slugs are stable product identifiers. Deployment details such as upstream
model IDs, credentials, endpoints, and protocols live in provider configuration,
not in this user-facing catalog.
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
    failover: tuple[str, ...]

    def public_dict(self) -> dict:
        value = asdict(self)
        value["tags"] = list(self.tags)
        value["failover"] = list(self.failover)
        return value


DEFAULT_CHAT_MODEL = "gemini-3.1"

MODEL_CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        "gemini-3.1",
        "双子座 3.1",
        "双子座",
        ("🚗高手", "粘人小狗"),
        "氛围一到就贴上来，甜和野都接得住",
        0.5,
        ("claude-haiku-4.5",),
    ),
    ModelSpec(
        "deepseek-v4-flash",
        "DeepSeek V4 Flash",
        "DeepSeek",
        ("嘴快小狗", "秒接梗"),
        "回复利落，适合轻松日常和快速斗嘴",
        1,
        ("deepseek-v4-pro", "gpt-5.5", "gemini-3.1"),
    ),
    ModelSpec(
        "deepseek-v4-pro",
        "DeepSeek V4 Pro",
        "DeepSeek",
        ("高智商", "会接戏"),
        "听得懂潜台词，剧情推进更稳",
        1,
        ("deepseek-v4-flash", "gpt-5.5", "gemini-3.1"),
    ),
    ModelSpec(
        "claude-haiku-4.5",
        "小克 Haiku 4.5",
        "小克",
        ("活泼小狗", "嘴甜型"),
        "轻快会夸，日常陪聊没有压力",
        0.5,
        ("gemini-3.1",),
    ),
    ModelSpec(
        "claude-sonnet-4.6",
        "小克 Sonnet 4.6",
        "小克",
        ("细腻高手", "很会拉扯"),
        "情绪接得准，暧昧推进自然",
        2,
        ("gpt-5.6-luna", "gpt-5.6-sol", "gemini-3.1"),
    ),
    ModelSpec(
        "claude-opus-4.6",
        "小克 Opus 4.6",
        "小克",
        ("顶级男主", "戏感拉满"),
        "强情节、高张力场面更有代入感",
        3,
        ("claude-opus-5", "claude-sonnet-4.6", "gemini-3.1"),
    ),
    ModelSpec(
        "claude-opus-5",
        "小克 Opus 5",
        "小克",
        ("白月光", "后劲很大"),
        "克制深情，适合重要剧情和长线关系",
        3,
        ("claude-opus-4.6", "claude-sonnet-4.6", "gemini-3.1"),
    ),
    ModelSpec(
        "grok-4.5",
        "Grok 4.5",
        "Grok",
        ("坏嘴男友", "越怼越亲"),
        "会接挑衅，适合欢喜冤家式互动",
        1,
        ("grok-4.6", "gpt-5.5", "gemini-3.1"),
    ),
    ModelSpec(
        "grok-4.6",
        "Grok 4.6",
        "Grok",
        ("疯批男主", "不按套路"),
        "反应出其不意，适合刺激型剧情",
        1,
        ("grok-4.5", "gpt-5.5", "gemini-3.1"),
    ),
    ModelSpec(
        "gpt-5.6-luna",
        "GPT-5.6 Luna",
        "GPT",
        ("温柔学长", "很会哄人"),
        "稳定温柔，低落时更有陪伴感",
        2,
        ("gpt-5.6-sol", "claude-sonnet-4.6", "gemini-3.1"),
    ),
    ModelSpec(
        "gpt-5.5",
        "GPT-5.5",
        "GPT",
        ("全能男友", "什么都能聊"),
        "日常、剧情、情绪都均衡",
        1,
        ("deepseek-v4-pro", "grok-4.5", "gemini-3.1"),
    ),
    ModelSpec(
        "gpt-5.6-sol",
        "GPT-5.6 Sol",
        "GPT",
        ("阳光小狗", "直球高手"),
        "热烈主动，不让暧昧一直卡住",
        2,
        ("gpt-5.6-luna", "claude-sonnet-4.6", "gemini-3.1"),
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
