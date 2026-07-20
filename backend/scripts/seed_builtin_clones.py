"""Seed built-in rin/dorothy voices as dual MiMo + Fish clones (issue 3).

For each built-in character this creates TWO ``character_voices`` rows:

  - **mimo** clone (日常语音): zero-shot. Stages the reference audio under
    ``assets/reference_voices/`` and stores its path in ``clone_audio_url``.
    The MiMo provider base64-encodes it at synth time (voiceclone model). No API
    call, no cost.
  - **fish** clone (真人语音): uploads the audio to Fish ``POST /voices``
    (multipart field ``audioFiles``) → a persistent ``voiceId`` stored in
    ``clone_voice_id``. This is a LIVE, PAID Fish Audio call.

Idempotent: rows are upserted per provider (compound key since migration 039),
so re-running is safe. A character that already has a ``ready`` fish row keeps
its existing ``clone_voice_id`` — the paid Fish clone is skipped unless
``--force`` is passed. Nothing is deleted.

Usage (from backend/):
    # Built-in rin + dorothy:
    python scripts/seed_builtin_clones.py \
        --rin /path/to/rin.wav \
        --dorothy /path/to/dorothy.mp3

    # Any single character (for backend-added characters):
    python scripts/seed_builtin_clones.py --character <char_id> --audio /path/to/timbre.wav

    # Only (re)stage the MiMo reference rows, skip the paid Fish clone:
    python scripts/seed_builtin_clones.py --rin ... --dorothy ... --skip-fish

    # Re-clone Fish even if a ready row exists (pays again):
    python scripts/seed_builtin_clones.py --rin ... --dorothy ... --force

Prerequisites: DB migrated to >= 039; FISH_API_KEY/FISH_BASE_URL/FISH_MODEL
set in .env (unless --skip-fish).
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
from pathlib import Path

import structlog
from sqlalchemy import text

from heart.core.config import settings

logger = structlog.get_logger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BACKEND_ROOT / "assets" / "reference_voices"

_MIME_BY_SUFFIX = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
}


def _stage_mimo_reference(character_id: str, source: Path) -> str:
    """Copy the reference audio into the stable assets dir; return its abs path."""
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = REFERENCE_DIR / f"{character_id}{source.suffix.lower()}"
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return str(target.resolve())


async def _fish_clone(character_id: str, source: Path) -> str:
    """Upload the reference to Fish Audio and return the new model_id (paid)."""
    from heart.ss08_voice.fish_provider import FishProvider

    if not settings.fish_api_key:
        raise SystemExit("FISH_API_KEY 未配置，无法做 Fish 克隆（或用 --skip-fish）")

    provider = FishProvider(
        api_key=settings.fish_api_key,
        base_url=settings.fish_base_url,
        model=settings.fish_model,
    )
    audio = source.read_bytes()
    mime = _MIME_BY_SUFFIX.get(source.suffix.lower(), "audio/wav")
    model_id = await provider.clone_from_bytes(
        audio, title=f"yuoyuo_{character_id}", filename=source.name, mime=mime
    )
    logger.info("fish_clone_created", character_id=character_id, model_id=model_id)
    return model_id


async def _existing_ready_fish_voice_id(db, character_id: str) -> str | None:
    """Return the clone_voice_id of a ready fish row, if one already exists."""
    row = await db.execute(
        text("""
            SELECT clone_voice_id FROM character_voices
            WHERE character_id = :cid AND voice_provider = 'fish'
              AND clone_status = 'ready' AND clone_voice_id IS NOT NULL
        """),
        {"cid": character_id},
    )
    return row.scalar_one_or_none()


async def _seed_character(
    db, character_id: str, source: Path, skip_fish: bool, force: bool
) -> None:
    # Verify the character exists (FK target).
    exists = await db.execute(
        text("SELECT 1 FROM characters WHERE id = :cid"), {"cid": character_id}
    )
    if exists.scalar_one_or_none() is None:
        print(f"  ! 角色 {character_id} 不存在，跳过")
        return

    # MiMo reference (zero-shot): stage the file and upsert the mimo row. Free.
    mimo_ref = _stage_mimo_reference(character_id, source)
    await db.execute(
        text("""
            INSERT INTO character_voices
                (character_id, user_id, voice_type, clone_audio_url,
                 clone_status, voice_provider)
            VALUES (:cid, NULL, 'clone', :ref, 'ready', 'mimo')
            ON CONFLICT (character_id, voice_provider) DO UPDATE
                SET voice_type = 'clone', clone_audio_url = :ref,
                    clone_status = 'ready', error_msg = NULL, updated_at = NOW()
        """),
        {"cid": character_id, "ref": mimo_ref},
    )

    # Fish clone (真人语音): reuse an existing ready voiceId unless --force, so
    # re-runs don't re-pay. Only clone (paid) when there's nothing to reuse.
    fish_voice_id: str | None = None
    reused = False
    if not skip_fish:
        if not force:
            fish_voice_id = await _existing_ready_fish_voice_id(db, character_id)
            reused = fish_voice_id is not None
        if fish_voice_id is None:
            fish_voice_id = await _fish_clone(character_id, source)

    if fish_voice_id:
        await db.execute(
            text("""
                INSERT INTO character_voices
                    (character_id, user_id, voice_type, clone_voice_id,
                     clone_status, voice_provider)
                VALUES (:cid, NULL, 'clone', :vid, 'ready', 'fish')
                ON CONFLICT (character_id, voice_provider) DO UPDATE
                    SET voice_type = 'clone', clone_voice_id = :vid,
                        clone_status = 'ready', error_msg = NULL, updated_at = NOW()
            """),
            {"cid": character_id, "vid": fish_voice_id},
        )
    await db.execute(
        text("UPDATE characters SET has_voice = TRUE WHERE id = :cid"),
        {"cid": character_id},
    )
    await db.commit()
    _fish_note = (
        f"{fish_voice_id}{' (reused)' if reused else ''}" if fish_voice_id else "skipped"
    )
    print(f"  ✓ {character_id}: mimo(ref={Path(mimo_ref).name}) fish({_fish_note})")


async def _main(targets: list[tuple[str, Path]], skip_fish: bool, force: bool) -> None:
    from heart.api.wiring import get_db_session_factory

    factory = get_db_session_factory()
    if factory is None:
        raise SystemExit("DB session factory 不可用（检查 DATABASE_URL）")

    async with factory() as db:
        for character_id, source in targets:
            if not source.exists():
                print(f"  ! 音频文件不存在: {source}，跳过 {character_id}")
                continue
            print(f"→ 播种 {character_id} ← {source}")
            await _seed_character(db, character_id, source, skip_fish, force)
    print("完成。")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed built-in / new-character mimo+fish clones")
    ap.add_argument("--rin", default="/Users/wanglixun/Downloads/test/rin.wav")
    ap.add_argument("--dorothy", default="/Users/wanglixun/Downloads/test/dorothy.mp3")
    ap.add_argument("--character", help="单个角色 id（配合 --audio，用于后台新增角色）")
    ap.add_argument("--audio", help="单个角色的音色文件路径（配合 --character）")
    ap.add_argument(
        "--skip-fish",
        action="store_true",
        help="只播种 MiMo 参考音色，不做付费 Fish 克隆",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="即使已有 ready 的 fish 行也重新克隆（会再次付费）",
    )
    args = ap.parse_args()

    if args.character:
        if not args.audio:
            raise SystemExit("--character 需要配合 --audio 指定音色文件")
        targets = [(args.character, Path(args.audio))]
    else:
        targets = [("rin", Path(args.rin)), ("dorothy", Path(args.dorothy))]
    asyncio.run(_main(targets, args.skip_fish, args.force))


if __name__ == "__main__":
    main()
