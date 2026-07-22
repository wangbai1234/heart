"""Data models for SS09 story mode.

Plain dataclasses mirroring the migration-042 tables plus the shared player
identity template. These are internal transfer objects; the HTTP layer
(routes_story.py) maps them to Pydantic response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Fixed genre enum (mirrors the importer's classification target).
GENRES: tuple[str, ...] = (
    "校园恋爱",
    "悬疑",
    "末日无限流",
    "修仙",
    "古风宫斗",
    "现代豪门",
    "西幻",
    "其他",
)

# The global default "主控" (player) character-card template. Scenarios may
# override via story_scenarios.player_template_json; when empty this is used.
# The player fills these before a run starts (see StartRunSheet on the frontend).
DEFAULT_PLAYER_TEMPLATE: dict[str, Any] = {
    "fields": [
        {"key": "name", "label": "姓名", "type": "text", "required": True},
        {"key": "age", "label": "年龄", "type": "text", "required": False},
        {
            "key": "gender",
            "label": "性别",
            "type": "select",
            "required": True,
            "options": ["男", "女", "双性"],
        },
        {"key": "appearance", "label": "外貌", "type": "textarea", "required": False},
        {"key": "personality", "label": "性格", "type": "textarea", "required": False},
        {"key": "zodiac", "label": "星座", "type": "text", "required": False},
        {"key": "mbti", "label": "MBTI", "type": "text", "required": False},
        {"key": "identity", "label": "身份", "type": "text", "required": False},
        {"key": "background", "label": "生平经历", "type": "textarea", "required": False},
    ]
}


@dataclass
class Scenario:
    """A row from ``story_scenarios``."""

    id: UUID
    slug: str
    title: str
    genre: str
    cover_url: Optional[str]
    blurb: str
    maturity: str  # 'all_ages' | 'adult'
    gm_system_prompt: str
    player_template_json: dict[str, Any]
    status: str
    is_featured: bool
    play_count: int


@dataclass
class Run:
    """A row from ``story_runs``."""

    id: UUID
    user_id: UUID
    scenario_id: UUID
    player_identity_json: dict[str, Any]
    title: str
    summary: str
    summary_watermark: int
    turn_count: int
    status: str
    model: str
    created_at: datetime
    last_activity_at: datetime


@dataclass
class StoryMessage:
    """A row from ``story_messages``."""

    id: UUID
    run_id: UUID
    turn_id: UUID
    seq: int
    role: str  # 'player' | 'gm' | 'npc' | 'system'
    kind: str  # 'narration' | 'dialogue' | 'action'
    npc_name: Optional[str]
    content: str
    created_at: datetime


@dataclass
class ScenarioCard:
    """Lightweight projection for list/browse endpoints."""

    id: UUID
    title: str
    genre: str
    cover_url: Optional[str]
    blurb: str
    maturity: str  # display-only label ('all_ages' | 'adult'); not access-gated
    is_featured: bool
    play_count: int

    extra: dict[str, Any] = field(default_factory=dict)
