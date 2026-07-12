"""032 — Repoint the "温柔女声" preset from female-wenrou to female-tianmei.

Rationale
=========

Migration 025 seeded ``female_warm.voice_id = 'female-wenrou'``. MiniMax T2A
v2 rejects that voice_id for our account with::

    {"base_resp": {"status_code": 2042,
                   "status_msg": "you don't have access to this voice_id"}}

Confirmed 2026-07-12 via ``backend/scripts/diag_voice_preset.py`` — the other
five active preset voices (rin_default / dorothy_default / male_neutral /
male_badao / male_jingying) all synthesize fine; only ``female-wenrou`` errors.
Probing MiniMax's female system voices found ``female-tianmei`` (甜美女声) is
accessible with the same account and is the closest fit for the "温柔" name.

We also flush the in-process sample cache reference by way of the id change:
``_PRESET_SAMPLE_CACHE`` is keyed by ``preset_id`` (unchanged), but the
underlying MiniMax audio is re-synthesized on next request because the row's
voice_id changed. A backend restart after applying this migration guarantees
the cache is empty.
"""

from alembic import op

revision = "032_female_warm_voice_id_tianmei"
down_revision = "031_preset_voice_sample_endpoint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE preset_voices
        SET voice_id = 'female-tianmei'
        WHERE id = 'female_warm' AND voice_id = 'female-wenrou'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE preset_voices
        SET voice_id = 'female-wenrou'
        WHERE id = 'female_warm' AND voice_id = 'female-tianmei'
    """)
