"""031 — Point preset_voices.sample_url at the backend TTS proxy endpoint.

Migration 030 seeded these URLs with `https://cdn.yuoyuo.app/voice-samples/*.mp3`,
which return 404 in every environment (the CDN files were never uploaded).  The
preview ▶ button rendered because `sample_url` was non-null, but clicking it
silently failed via `audio.play().catch(() => {})`.

We now serve the samples through
``GET /api/voice/presets/{preset_id}/sample``, which synthesizes ~2 s of MP3
via MiniMax TTS and caches it in-process.  This migration rewrites the six
seed rows to point at that endpoint.  The frontend fetches the URL with the
user's Bearer token and pipes the blob into an ``Audio`` element.
"""

from alembic import op

revision = "031_preset_voice_sample_endpoint"
down_revision = "030_preset_voice_sample_urls"
branch_labels = None
depends_on = None

_PRESET_IDS = (
    "rin_default",
    "dorothy_default",
    "female_warm",
    "male_neutral",
    "male_badao",
    "male_jingying",
)


def upgrade() -> None:
    op.execute(
        """
        UPDATE preset_voices
        SET sample_url = '/api/voice/presets/' || id || '/sample'
        WHERE id IN ('rin_default', 'dorothy_default', 'female_warm',
                     'male_neutral', 'male_badao', 'male_jingying')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE preset_voices SET sample_url = 'https://cdn.yuoyuo.app/voice-samples/female-shaonv.mp3'
        WHERE id = 'rin_default'
        """
    )
    op.execute(
        """
        UPDATE preset_voices SET sample_url = 'https://cdn.yuoyuo.app/voice-samples/female-yujie.mp3'
        WHERE id = 'dorothy_default'
        """
    )
    op.execute(
        """
        UPDATE preset_voices SET sample_url = 'https://cdn.yuoyuo.app/voice-samples/female-wenrou.mp3'
        WHERE id = 'female_warm'
        """
    )
    op.execute(
        """
        UPDATE preset_voices SET sample_url = 'https://cdn.yuoyuo.app/voice-samples/male-qn-qingse.mp3'
        WHERE id = 'male_neutral'
        """
    )
    op.execute(
        """
        UPDATE preset_voices SET sample_url = 'https://cdn.yuoyuo.app/voice-samples/male-qn-badao.mp3'
        WHERE id = 'male_badao'
        """
    )
    op.execute(
        """
        UPDATE preset_voices SET sample_url = 'https://cdn.yuoyuo.app/voice-samples/male-qn-jingying.mp3'
        WHERE id = 'male_jingying'
        """
    )
