"""060 — Seed Fish preset voices (4 male + 4 female).

Adds eight preset_voices rows with provider='fish'. Each voice_id is a Fish
Audio voice UUID (model_id) supplied by product; the Fish provider resolves it
directly for both preview synthesis and realtime streaming. These replace the
MiMo presets in the character-creation picker (MiMo is retained in the table
for ASR + legacy characters, but hidden from the picker by routes_voice).

All INSERTs are idempotent (ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

from alembic import op

revision = "060_fish_preset_voices"
down_revision = "059_kind_transfer"
branch_labels = None
depends_on = None

# (id, name, voice_id (Fish UUID), provider, description, gender)
_MALE_ROWS = [
    ("fish_male_bad", "危险痞帅", "2fe2aecb-8a8b-45b1-9de1-ddede0c4da63", "fish", "痞气张扬，危险又撩人的坏男孩音", "male"),
    ("fish_male_uncle", "轻熟男", "4802fb05-e5ea-4fe0-b9b4-a5ca48651672", "fish", "沉稳克制，成熟温润的轻熟男声", "male"),
    ("fish_male_yandere", "偏执病娇", "5669876b-1354-438b-b79a-3927249691bb", "fish", "偏执深情，温柔里藏着占有欲", "male"),
    ("fish_male_loyal", "忠犬暖男", "d3be1f83-1dfa-42bf-b819-81659deeac35", "fish", "温暖专一，宠溺贴心的忠犬暖男", "male"),
]

_FEMALE_ROWS = [
    ("fish_female_senior", "台湾腔学姐音", "25129630-581c-4cd8-9fa1-12199fcc9f0b", "fish", "软糯台湾腔，亲昵撒娇的学姐音", "female"),
    ("fish_female_gentle", "温柔女声", "ff66d8d5-818f-43a8-9b6b-7936b6e75900", "fish", "温柔细腻，轻声细语的治愈女声", "female"),
    ("fish_female_yujie", "御姐女声", "2ded03d1-316d-457a-a527-a3cd082e5d05", "fish", "低沉磁性，成熟自信的御姐音", "female"),
    ("fish_female_jp_sweet", "日语甜美女声", "e5a2c2fd-12f8-425e-9783-05bcdc905b0b", "fish", "甜美软萌，日系少女的娇俏嗓音", "female"),
]


def upgrade() -> None:
    rows = _MALE_ROWS + _FEMALE_ROWS
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
    ids = ", ".join(f"'{id_}'" for id_, *_ in (_MALE_ROWS + _FEMALE_ROWS))
    op.execute(f"DELETE FROM preset_voices WHERE id IN ({ids})")  # noqa: S608
