"""Seed built-in rin/dorothy voices as dual MiMo + Fish clones (issue 3).

For each built-in character this creates TWO ``character_voices`` rows:

  - **mimo** clone (日常语音): zero-shot. Stages the reference audio under
    ``assets/reference_voices/`` and stores its path in ``clone_audio_url``.
    The MiMo provider base64-encodes it at synth time (voiceclone model). No API
    call, no cost.
  - **fish** clone (真人语音): uploads the audio to Fish ``/model`` → a
    persistent ``model_id`` stored in ``clone_voice_id``. This is a LIVE, PAID
    Fish Audio call.

Any pre-existing rows for the character (e.g. the legacy MiniMax preset seeded
in migration 025) are removed first, so the character ends up with exactly the
mimo + fish rows.

Usage (from backend/):
    python scripts/seed_builtin_clones.py \
        --rin /Users/wanglixun/Downloads/test/rin.wav \
        --dorothy /Users/wanglixun/Downloads/test/dorothy.mp3

    # Only (re)stage the MiMo reference rows, skip the paid Fish clone:
    python scripts/seed_builtin_clones.py --rin ... --dorothy ... --skip-fish

Prerequisites: dev DB migrated to >= 039; FISH_API_KEY/FISH_BASE_URL/FISH_MODEL
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


async def _seed_character(db, character_id: str, source: Path, skip_fish: bool) -> None:
    # Verify the character exists (FK target).
    exists = await db.execute(
        text("SELECT 1 FROM characters WHERE id = :cid"), {"cid": character_id}
    )
    if exists.scalar_one_or_none() is None:
        print(f"  ! 角色 {character_id} 不存在，跳过")
        return

    mimo_ref = _stage_mimo_reference(character_id, source)
    fish_model_id = None if skip_fish else await _fish_clone(character_id, source)

    # Replace any existing rows for this character with the mimo (+ fish) clones.
    await db.execute(
        text("DELETE FROM character_voices WHERE character_id = :cid"),
        {"cid": character_id},
    )
    await db.execute(
        text("""
            INSERT INTO character_voices
                (character_id, user_id, voice_type, clone_audio_url,
                 clone_status, voice_provider)
            VALUES (:cid, NULL, 'clone', :ref, 'ready', 'mimo')
        """),
        {"cid": character_id, "ref": mimo_ref},
    )
    if fish_model_id:
        await db.execute(
            text("""
                INSERT INTO character_voices
                    (character_id, user_id, voice_type, clone_voice_id,
                     clone_status, voice_provider)
                VALUES (:cid, NULL, 'clone', :vid, 'ready', 'fish')
            """),
            {"cid": character_id, "vid": fish_model_id},
        )
    await db.execute(
        text("UPDATE characters SET has_voice = TRUE WHERE id = :cid"),
        {"cid": character_id},
    )
    await db.commit()
    print(f"  ✓ {character_id}: mimo(ref={Path(mimo_ref).name}) fish({fish_model_id or 'skipped'})")


async def _main(rin: Path, dorothy: Path, skip_fish: bool) -> None:
    from heart.api.wiring import get_db_session_factory

    factory = get_db_session_factory()
    if factory is None:
        raise SystemExit("DB session factory 不可用（检查 DATABASE_URL）")

    targets = [("rin", rin), ("dorothy", dorothy)]
    async with factory() as db:
        for character_id, source in targets:
            if not source.exists():
                print(f"  ! 音频文件不存在: {source}，跳过 {character_id}")
                continue
            print(f"→ 播种 {character_id} ← {source}")
            await _seed_character(db, character_id, source, skip_fish)
    print("完成。")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed rin/dorothy mimo+fish clones")
    ap.add_argument("--rin", default="/Users/wanglixun/Downloads/test/rin.wav")
    ap.add_argument("--dorothy", default="/Users/wanglixun/Downloads/test/dorothy.mp3")
    ap.add_argument(
        "--skip-fish",
        action="store_true",
        help="只播种 MiMo 参考音色，不做付费 Fish 克隆",
    )
    args = ap.parse_args()
    asyncio.run(_main(Path(args.rin), Path(args.dorothy), args.skip_fish))


if __name__ == "__main__":
    main()
