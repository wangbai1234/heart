"""030 — Seed sample_url for all 6 built-in preset voices.

The voice preset cards in the character-creation UI show a preview button only
when sample_url IS NOT NULL.  All 6 rows currently have NULL, so no preview
button ever appears.

This migration backfills sample_url with short (~10 s) voice-demo MP3s hosted on
the project CDN.  The actual audio files must be uploaded to the same paths
before production deployment:

    PUT /voice-samples/female-shaonv.mp3      ← rin_default
    PUT /voice-samples/female-yujie.mp3       ← dorothy_default
    PUT /voice-samples/female-wenrou.mp3      ← female_warm
    PUT /voice-samples/male-qn-qingse.mp3    ← male_neutral
    PUT /voice-samples/male-qn-badao.mp3     ← male_badao
    PUT /voice-samples/male-qn-jingying.mp3  ← male_jingying

The URLs below use the production CDN prefix; in dev they will 404 when clicked
(preview button appears but plays nothing), which is acceptable for local dev.
"""

from alembic import op

revision = "030_preset_voice_sample_urls"
down_revision = "029_read_state"
branch_labels = None
depends_on = None

_CDN = "https://cdn.yuoyuo.app/voice-samples"


def upgrade() -> None:
    op.execute(f"""
        UPDATE preset_voices SET sample_url = '{_CDN}/female-shaonv.mp3'
        WHERE id = 'rin_default'      AND sample_url IS NULL
    """)
    op.execute(f"""
        UPDATE preset_voices SET sample_url = '{_CDN}/female-yujie.mp3'
        WHERE id = 'dorothy_default'  AND sample_url IS NULL
    """)
    op.execute(f"""
        UPDATE preset_voices SET sample_url = '{_CDN}/female-wenrou.mp3'
        WHERE id = 'female_warm'      AND sample_url IS NULL
    """)
    op.execute(f"""
        UPDATE preset_voices SET sample_url = '{_CDN}/male-qn-qingse.mp3'
        WHERE id = 'male_neutral'     AND sample_url IS NULL
    """)
    op.execute(f"""
        UPDATE preset_voices SET sample_url = '{_CDN}/male-qn-badao.mp3'
        WHERE id = 'male_badao'       AND sample_url IS NULL
    """)
    op.execute(f"""
        UPDATE preset_voices SET sample_url = '{_CDN}/male-qn-jingying.mp3'
        WHERE id = 'male_jingying'    AND sample_url IS NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE preset_voices SET sample_url = NULL
        WHERE id IN (
            'rin_default', 'dorothy_default', 'female_warm',
            'male_neutral', 'male_badao', 'male_jingying'
        )
    """)
