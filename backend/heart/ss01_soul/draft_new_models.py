"""新增模型定义 - UGC 创建重构批 1

这些模型会被集成到 draft.py 的 CharacterDraft 中。
单独文件是为了保持 review clarity。
"""

from __future__ import annotations

import re
from typing import Annotated, Literal, Optional, Union

from pydantic import AfterValidator, BaseModel, Field

# ── 色值白名单验证器 ──
_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}"
    r"|rgba?\([\d\s.,%]+\)"
    r"|linear-gradient\([^;{}()]*(\([^;{}()]*\))?[^;{}()]*\)"
    r"|[\d.]+(?:px)?\s+[\d.]+px\s+[\d.]+px\s+rgba?\([^)]+\))$"
)


def _check_color(v: str) -> str:
    """验证色值白名单。禁止 CSS 注入字符。"""
    if not _COLOR_RE.match(v):
        raise ValueError(f"Invalid color value: {v}")
    # 禁止 CSS 注入关键字符
    forbidden = [";", "{", "}", "url(", "expression(", "javascript:"]
    for token in forbidden:
        if token in v.lower():
            raise ValueError(f"Forbidden token in color: {token}")
    return v


ColorStr = Annotated[str, Field(max_length=200), AfterValidator(_check_color)]


# ── 配色 (14 槽位) ──
class ChromeDraft(BaseModel, extra="forbid"):
    """14 槽位配色。字段名与前端 ChromePalette 严格一致
    (web/src/pages/CharacterProfilePage.tsx:70-85)，勿改名。
    camelCase 字段名是为了与前端保持一致，违反 Python 命名规范但必须保留。
    """

    bg: ColorStr
    coverBg: ColorStr  # noqa: N815
    scrimGradient: ColorStr  # noqa: N815
    nameColor: ColorStr  # noqa: N815
    ageColor: ColorStr  # noqa: N815
    taglineColor: ColorStr  # noqa: N815
    chipActiveBg: ColorStr  # noqa: N815
    chipActiveBorder: ColorStr  # noqa: N815
    chipActiveText: ColorStr  # noqa: N815
    chipInactiveBg: ColorStr  # noqa: N815
    chipInactiveBorder: ColorStr  # noqa: N815
    chipInactiveText: ColorStr  # noqa: N815
    ctaGradient: ColorStr  # noqa: N815
    ctaShadow: ColorStr  # noqa: N815


# ── PremiseCard 相关 ──
class PremiseRowDraft(BaseModel, extra="forbid"):
    label: Annotated[str, Field(max_length=24)]
    value: Annotated[str, Field(max_length=120)]


class PremiseCardDraft(BaseModel, extra="forbid"):
    """字段对齐既有 PremiseCardData
    (web/src/components/characterProfiles/PremiseCardBase.tsx:9-22)。
    注意 warning 是字符串消息，不是布尔开关。
    leadIn 保持 camelCase 与前端一致。
    """

    accent: ColorStr
    leadIn: Annotated[str, Field(max_length=400)]  # noqa: N815
    title: Annotated[str, Field(max_length=60)]
    rows: list[PremiseRowDraft] = Field(default_factory=list, max_length=6)
    note: Optional[Annotated[str, Field(max_length=300)]] = None
    warning: Optional[Annotated[str, Field(max_length=120)]] = None


# ── ProfileBlocks (区块编辑器) ──
class ProfileBlockBase(BaseModel, extra="forbid"):
    type: str


class DossierBlock(ProfileBlockBase):
    """档案表（病历卡/身份档案）"""

    type: Literal["dossier"]
    title: Annotated[str, Field(max_length=40)]
    rows: list[PremiseRowDraft] = Field(min_length=1, max_length=10)


class QuoteBlock(ProfileBlockBase):
    """大字引文（serif 独白）"""

    type: Literal["quote"]
    text: Annotated[str, Field(max_length=200)]
    attribution: Optional[Annotated[str, Field(max_length=40)]] = None


class TimelineBlock(ProfileBlockBase):
    """纵向时间线"""

    type: Literal["timeline"]
    title: Annotated[str, Field(max_length=40)]
    events: list[PremiseRowDraft] = Field(min_length=1, max_length=8)


class ObjectsBlock(ProfileBlockBase):
    """物件隐喻"""

    type: Literal["objects"]
    title: Annotated[str, Field(max_length=40)]
    items: list[PremiseRowDraft] = Field(min_length=1, max_length=6)


class ContrastBlock(ProfileBlockBase):
    """对照（表里反差）"""

    type: Literal["contrast"]
    leftLabel: Annotated[str, Field(max_length=20)]  # noqa: N815
    rightLabel: Annotated[str, Field(max_length=20)]  # noqa: N815
    pairs: list[PremiseRowDraft] = Field(min_length=1, max_length=6)


class ProseBlock(ProfileBlockBase):
    """纯文本段落"""

    type: Literal["prose"]
    title: Optional[Annotated[str, Field(max_length=40)]] = None
    text: Annotated[str, Field(max_length=600)]


ProfileBlock = Annotated[
    Union[
        DossierBlock,
        QuoteBlock,
        TimelineBlock,
        ObjectsBlock,
        ContrastBlock,
        ProseBlock,
    ],
    Field(discriminator="type"),
]


# ── StarterConfig (聊天开场选项) ──
class StarterFlat(BaseModel, extra="forbid"):
    """平铺式开场选项 (1-5条)"""

    type: Literal["flat"]
    prompts: list[Annotated[str, Field(max_length=60)]] = Field(min_length=1, max_length=5)


class StarterBranch(BaseModel, extra="forbid"):
    """分支式开场的一个分支"""

    label: Annotated[str, Field(max_length=12)]  # 切入角度
    lines: list[Annotated[str, Field(max_length=60)]] = Field(min_length=1, max_length=3)


class StarterBranched(BaseModel, extra="forbid"):
    """分支式开场选项 (2-4个分支)"""

    type: Literal["branched"]
    branches: list[StarterBranch] = Field(min_length=2, max_length=4)


StarterConfig = Annotated[
    Union[StarterFlat, StarterBranched],
    Field(discriminator="type"),
]
