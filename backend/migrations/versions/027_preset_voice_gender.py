"""027 — Add preset_voices.gender + seed 2 additional male voices.

The character creation flow now filters preset voices by the character's
gender. Backfills the existing 4 seed rows and adds 2 additional male
options from MiniMax's built-in catalog so male characters get parity
with female (3 female + 1 male → 3 female + 3 male).

The pre-existing 'male_neutral' seed row is renamed to '青涩男声' since it
uses MiniMax's 'male-qn-qingse' voice_id — the "neutral" label was misleading.
"""

from alembic import op

revision = "027_preset_voice_gender"
down_revision = "026_message_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE preset_voices
            ADD COLUMN IF NOT EXISTS gender VARCHAR(8) NOT NULL DEFAULT 'female'
    """)
    op.execute("""
        ALTER TABLE preset_voices
            DROP CONSTRAINT IF EXISTS preset_voices_gender_check
    """)
    op.execute("""
        ALTER TABLE preset_voices
            ADD CONSTRAINT preset_voices_gender_check
            CHECK (gender IN ('male', 'female'))
    """)

    # Backfill existing seeds (all 3 existing 'female-*' rows are female; the
    # single 'male_neutral' row is male).
    op.execute("""
        UPDATE preset_voices SET gender = 'male'
        WHERE id IN ('male_neutral')
    """)
    op.execute("""
        UPDATE preset_voices SET gender = 'female'
        WHERE id IN ('rin_default', 'dorothy_default', 'female_warm')
    """)

    # Rename the pre-existing 'male_neutral' → '青涩男声' so the naming
    # matches MiniMax's voice_id (male-qn-qingse).
    op.execute("""
        UPDATE preset_voices
        SET name = '青涩男声',
            description = '清新自然，适合青年学生型角色'
        WHERE id = 'male_neutral'
    """)

    # Seed 2 additional male voices using MiniMax built-in voice IDs.
    op.execute("""
        INSERT INTO preset_voices (id, name, voice_id, provider, description, is_active, gender)
        VALUES
            ('male_badao',    '霸道男声', 'male-qn-badao',    'minimax',
                '低沉有力，适合霸道总裁型角色', TRUE, 'male'),
            ('male_jingying', '精英男声', 'male-qn-jingying', 'minimax',
                '成熟稳重，适合职场精英型角色', TRUE, 'male')
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM preset_voices
        WHERE id IN ('male_badao', 'male_jingying')
    """)
    op.execute("""
        UPDATE preset_voices
        SET name = '中性男声', description = '清澈男声'
        WHERE id = 'male_neutral'
    """)
    op.execute("ALTER TABLE preset_voices DROP CONSTRAINT IF EXISTS preset_voices_gender_check")
    op.execute("ALTER TABLE preset_voices DROP COLUMN IF EXISTS gender")
