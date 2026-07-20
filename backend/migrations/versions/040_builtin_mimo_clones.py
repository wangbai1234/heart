"""040 — Seed built-in rin/dorothy MiMo zero-shot clone rows.

Why this exists
---------------
rin/dorothy were seeded in migration 025 with a single ``preset`` +
``minimax`` row in ``character_voices``. Migration 036 backfilled their
``voice_provider`` to ``minimax``; 038 only added mimo entries to the
``preset_voices`` catalog (for UGC characters), and 039 merely relaxed the
uniqueness constraint. **No migration ever gave the built-in characters a
usable ``mimo`` voice row.**

The voice resolver (``ss08_voice/voice_resolver.py``) locks free-tier users to
``mimo`` (``_tts_allowed('free', p)`` is true only for ``mimo``). It looks up a
``ready`` row for ``mimo``, finds none for rin/dorothy, then falls back to any
tier-allowed ready row — but the only existing row is ``minimax``, which NO
tier is allowed to use (free=mimo; plus/immersive=mimo+fish). So
``resolve_effective_voice`` returns ``None`` and every turn silently degrades
to text. Symptom: user enables voice, still gets text, no error surfaced.

Fix (data-only)
---------------
Insert a ``mimo`` zero-shot clone row for rin/dorothy pointing at the reference
audio that already ships in the image (``backend/assets/reference_voices/``,
git-tracked, COPYed to ``/app/assets/...`` by the Dockerfile). The MiMo
provider base64-encodes the reference on each synth call (``mimo_provider.py::
_reference_data_uri``), which ``open()``s the path relative to the process CWD
— ``/app`` in the container (WORKDIR) and ``backend/`` in dev — so a RELATIVE
path resolves correctly in both environments (matches the ``.env``
``MIMO_REFERENCE_AUDIO_PATH`` convention). No absolute container path is baked
into the DB, keeping dev and prod portable.

Idempotent via ON CONFLICT on the (character_id, voice_provider) constraint
added in 039, so re-runs (or a DB where seed_builtin_clones.py was run by hand)
converge to the same relative path. The stale ``minimax`` rows are left in
place — they are inert (no tier can select them) and removing them is out of
scope here.

Revision ID: 040_builtin_mimo_clones
Revises: 039_dual_provider_voices
Create Date: 2026-07-20
"""

from __future__ import annotations

from alembic import op

revision = "040_builtin_mimo_clones"
down_revision = "039_dual_provider_voices"
branch_labels = None
depends_on = None

# (character_id, reference audio path relative to the backend/ root == process CWD)
_CLONES = [
    ("rin", "assets/reference_voices/rin.wav"),
    ("dorothy", "assets/reference_voices/dorothy.mp3"),
]


def upgrade() -> None:
    for character_id, ref_path in _CLONES:
        # Only seed for characters that actually exist (FK safety on partial DBs).
        op.execute(
            f"""
            INSERT INTO character_voices
                (character_id, user_id, voice_type, clone_audio_url,
                 clone_status, voice_provider)
            SELECT '{character_id}', NULL, 'clone', '{ref_path}', 'ready', 'mimo'
            WHERE EXISTS (SELECT 1 FROM characters WHERE id = '{character_id}')
            ON CONFLICT (character_id, voice_provider) DO UPDATE
                SET voice_type      = 'clone',
                    clone_audio_url = EXCLUDED.clone_audio_url,
                    clone_status    = 'ready',
                    preset_voice_id = NULL,
                    updated_at      = NOW()
            """  # noqa: S608 — no user input; character_id/ref_path are module constants
        )
        # Keep the denormalised hot-path flag consistent.
        op.execute(
            f"UPDATE characters SET has_voice = TRUE WHERE id = '{character_id}'"
        )


def downgrade() -> None:
    for character_id, _ in _CLONES:
        op.execute(
            f"""
            DELETE FROM character_voices
            WHERE character_id = '{character_id}' AND voice_provider = 'mimo'
              AND voice_type = 'clone'
            """
        )
