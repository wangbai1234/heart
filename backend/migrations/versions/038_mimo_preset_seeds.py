"""038 — Seed MiMo preset voices (5 female + 5 male).

Adds ten preset_voices rows with provider='mimo'.  Voice IDs match the keys
in heart.ss08_voice.mimo_provider._VOICE_DESCRIPTIONS so the MiMo provider
can resolve the correct natural-language voice profile for user-created
characters that select one of these presets.

All INSERTs are idempotent (ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

from alembic import op

revision = "038_mimo_preset_seeds"
down_revision = "037_invites"
branch_labels = None
depends_on = None

_FEMALE_ROWS = [
    ("mimo_female_gentle", "温柔少女", "mimo_female_gentle", "mimo", "温柔细腻，语调平缓温暖", "female"),
    ("mimo_female_cool", "飒爽御姐", "mimo_female_cool", "mimo", "低沉磁性，成熟自信", "female"),
    ("mimo_female_bright", "活泼甜美", "mimo_female_bright", "mimo", "明亮甜美，青春活力", "female"),
    ("mimo_female_elegant", "知性优雅", "mimo_female_elegant", "mimo", "沉静优雅，知性从容", "female"),
    ("mimo_female_shy", "内敛清澈", "mimo_female_shy", "mimo", "清澈纯净，略带羞涩", "female"),
]

_MALE_ROWS = [
    ("mimo_male_gentle", "温柔男声", "mimo_male_gentle", "mimo", "温暖细腻，体贴耐心", "male"),
    ("mimo_male_cool", "清冷男声", "mimo_male_cool", "mimo", "低沉疏离，冷峻克制", "male"),
    ("mimo_male_energetic", "阳光男声", "mimo_male_energetic", "mimo", "明亮爽朗，青春活力", "male"),
    ("mimo_male_mature", "成熟低沉", "mimo_male_mature", "mimo", "低沉磁性，稳重从容", "male"),
    ("mimo_male_sweet", "软糯暖男", "mimo_male_sweet", "mimo", "温软甜糯，暖心亲昵", "male"),
]


def upgrade() -> None:
    rows = _FEMALE_ROWS + _MALE_ROWS
    values = ", ".join(
        f"('{id_}', '{name}', '{voice_id}', '{provider}', '{desc}', TRUE, '{gender}')"
        for id_, name, voice_id, provider, desc, gender in rows
    )
    op.execute(f"""
        INSERT INTO preset_voices (id, name, voice_id, provider, description, is_active, gender)
        VALUES {values}
        ON CONFLICT (id) DO NOTHING
    """)  # noqa: S608 — no user input; all values are module-level constants


def downgrade() -> None:
    ids = ", ".join(f"'{id_}'" for id_, *_ in (_FEMALE_ROWS + _MALE_ROWS))
    op.execute(f"DELETE FROM preset_voices WHERE id IN ({ids})")
