"""041 — Point rin's MiMo clone reference at the compressed mono MP3.

Why
---
rin's reference shipped as a 44.1kHz **stereo PCM WAV** (2.4 MB → ~3.3 MB
base64). MiMo voiceclone is zero-shot and has NO persistent voice ID (per the
official docs), so that reference is base64-encoded and **re-uploaded on every
synth call** — a large fixed per-turn latency, especially on the overseas VPS.
It also cannot stream (低延迟流式输出暂未上线), so shrinking the upload is the
only available MiMo speed lever.

We re-encoded the reference to **mono 96 kbps MP3, full duration** (timbre is
preserved for zero-shot cloning; ~3.3 MB → ~228 KB base64, ~14×). The file was
renamed rin.wav → rin.mp3, so migration 040's clone_audio_url must follow.

dorothy was already .mp3 (only re-encoded to mono in place, same path), so only
rin's row needs updating here.

Idempotent: a plain UPDATE targeting rin's mimo clone row; safe to re-run.

Revision ID: 041_rin_mp3_reference
Revises: 040_builtin_mimo_clones
Create Date: 2026-07-20
"""

from __future__ import annotations

from alembic import op

revision = "041_rin_mp3_reference"
down_revision = "040_builtin_mimo_clones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE character_voices
        SET clone_audio_url = 'assets/reference_voices/rin.mp3',
            updated_at = NOW()
        WHERE character_id = 'rin'
          AND voice_provider = 'mimo'
          AND voice_type = 'clone'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE character_voices
        SET clone_audio_url = 'assets/reference_voices/rin.wav',
            updated_at = NOW()
        WHERE character_id = 'rin'
          AND voice_provider = 'mimo'
          AND voice_type = 'clone'
        """
    )
