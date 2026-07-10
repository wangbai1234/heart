"""025 — preset_voices, character_voices tables + has_voice on characters."""

from alembic import op

revision = "025_voice_tables"
down_revision = "024_sequence_id_and_centesimal_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # preset_voices: built-in voice catalog (seed rows inserted below)
    op.execute("""
        CREATE TABLE IF NOT EXISTS preset_voices (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            voice_id    TEXT NOT NULL,
            provider    TEXT NOT NULL DEFAULT 'minimax',
            description TEXT,
            sample_url  TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)

    # character_voices: one row per character; user_id non-null for UGC characters
    op.execute("""
        CREATE TABLE IF NOT EXISTS character_voices (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            character_id     TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
            user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
            voice_type       TEXT NOT NULL CHECK (voice_type IN ('preset', 'clone')),
            preset_voice_id  TEXT REFERENCES preset_voices(id),
            clone_audio_url  TEXT,
            clone_voice_id   TEXT,
            clone_status     TEXT NOT NULL DEFAULT 'pending'
                             CHECK (clone_status IN ('pending', 'processing', 'ready', 'failed')),
            error_msg        TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (character_id)
        )
    """)

    # Denormalised flag so list_characters can avoid a JOIN on the hot path
    op.execute("""
        ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS has_voice BOOLEAN NOT NULL DEFAULT FALSE
    """)

    # Seed preset voices for built-in characters
    op.execute("""
        INSERT INTO preset_voices (id, name, voice_id, provider, description, is_active)
        VALUES
            ('rin_default',     '凛 — 少女',  'female-shaonv', 'minimax', '清甜少女音，凛的默认音色', TRUE),
            ('dorothy_default', '多萝西 — 御姐', 'female-yujie',  'minimax', '成熟知性御姐音，多萝西的默认音色', TRUE),
            ('male_neutral',    '中性男声',  'male-qn-qingse', 'minimax', '清澈男声', TRUE),
            ('female_warm',     '温柔女声',  'female-wenrou',  'minimax', '温柔甜美女声', TRUE)
        ON CONFLICT (id) DO NOTHING
    """)

    # Pre-configure built-in characters so voice is immediately usable
    op.execute("""
        INSERT INTO character_voices (character_id, voice_type, preset_voice_id, clone_status)
        VALUES
            ('rin',     'preset', 'rin_default',     'ready'),
            ('dorothy', 'preset', 'dorothy_default', 'ready')
        ON CONFLICT (character_id) DO NOTHING
    """)

    op.execute("""
        UPDATE characters SET has_voice = TRUE
        WHERE id IN ('rin', 'dorothy')
    """)


def downgrade() -> None:
    op.execute("UPDATE characters SET has_voice = FALSE WHERE id IN ('rin', 'dorothy')")
    op.execute("ALTER TABLE characters DROP COLUMN IF EXISTS has_voice")
    op.execute("DROP TABLE IF EXISTS character_voices")
    op.execute("DROP TABLE IF EXISTS preset_voices")
