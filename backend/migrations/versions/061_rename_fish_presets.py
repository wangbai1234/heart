"""061 — Rename Fish preset voices for clearer, on-brand labels.

Migration 060 seeded the 8 Fish presets with working but rough names
(轻熟男 / 台湾腔学姐音 / 偏执病娇 …). Product feedback: the male labels and the
台湾 female label read unclearly. This UPDATEs name + description in place
(rows already exist from 060, so ON CONFLICT-style INSERT would be a no-op).
温柔女声 / 御姐女声 / 日语甜美女声 are already clear and left unchanged.

Idempotent: pure UPDATE keyed by id; safe to re-run.
"""

from __future__ import annotations

from alembic import op

revision = "061_rename_fish_presets"
down_revision = "060_fish_preset_voices"
branch_labels = None
depends_on = None

# (id, new_name, new_description) — only rows whose label changes.
_RENAMES = [
    ("fish_male_bad", "痞帅浪子", "痞气张扬，危险又撩人的坏男孩音"),
    ("fish_male_uncle", "温润绅士", "沉稳克制，成熟温润的轻熟绅士音"),
    ("fish_male_yandere", "深情病娇", "偏执深情，温柔里藏着占有欲的病娇音"),
    ("fish_male_loyal", "宠溺忠犬", "温暖专一，宠溺贴心的忠犬暖男音"),
    ("fish_female_senior", "台湾软妹音", "软糯台湾腔，亲昵撒娇的邻家软妹音"),
]

# Prior names (for downgrade) — mirrors migration 060.
_PRIOR = [
    ("fish_male_bad", "危险痞帅", "痞气张扬，危险又撩人的坏男孩音"),
    ("fish_male_uncle", "轻熟男", "沉稳克制，成熟温润的轻熟男声"),
    ("fish_male_yandere", "偏执病娇", "偏执深情，温柔里藏着占有欲"),
    ("fish_male_loyal", "忠犬暖男", "温暖专一，宠溺贴心的忠犬暖男"),
    ("fish_female_senior", "台湾腔学姐音", "软糯台湾腔，亲昵撒娇的学姐音"),
]


def _apply(rows: list[tuple[str, str, str]]) -> None:
    for id_, name, desc in rows:
        op.execute(
            "UPDATE preset_voices SET name = '{}', description = '{}' "
            "WHERE id = '{}'".format(
                name.replace("'", "''"), desc.replace("'", "''"), id_
            )
        )  # noqa: S608 — module-level constants only, no user input


def upgrade() -> None:
    _apply(_RENAMES)


def downgrade() -> None:
    _apply(_PRIOR)
