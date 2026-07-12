"""Diagnose preset-voice TTS synthesis, one row at a time.

Iterates every ``is_active`` row in ``preset_voices`` and calls MiniMax T2A
with that voice_id + a short Chinese sample sentence, printing the outcome so
we can identify which built-in preset (if any) is broken at the provider layer
(e.g. voice_id renamed / removed by the vendor).

The frontend "试听失败" toast only tells us a request failed; this tool tells
us WHY.  Run it after a real-device report where a specific preset's ▶ button
does not play — the preset row emitting a non-OK response is your culprit.

Usage:
  cd backend
  python3.11 scripts/diag_voice_preset.py             # all active presets
  python3.11 scripts/diag_voice_preset.py --id female_warm   # single row

Requires .env with MINIMAX_API_KEY and DATABASE_URL_ASYNC populated.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from heart.core.config import settings
from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.minimax_provider import MiniMaxProvider
from heart.ss08_voice.types import TTSRequest

_SAMPLE_TEMPLATE = "你好，我是{name}，很高兴认识你，希望我们能聊得愉快。"


async def _probe_one(provider: MiniMaxProvider, preset_id: str, name: str, voice_id: str) -> bool:
    """Try a synthesize call for a single preset row. Returns True on success."""
    print(f"→ {preset_id:<20} name={name!r:<20} voice_id={voice_id!r}", flush=True)
    try:
        result = await provider.synthesize(
            TTSRequest(text=_SAMPLE_TEMPLATE.format(name=name), voice_id=voice_id)
        )
    except TTSProviderError as exc:
        print(f"  ✗ TTSProviderError status={exc.status_code} msg={exc}", flush=True)
        return False
    except Exception as exc:
        print(f"  ✗ {type(exc).__name__}: {exc}", flush=True)
        return False
    print(f"  ✓ ok bytes={len(result.audio)} duration_ms={result.duration_ms}", flush=True)
    return True


async def _main(preset_filter: str | None) -> int:
    if not settings.minimax_api_key:
        print("MINIMAX_API_KEY missing — nothing to probe. Populate .env first.", file=sys.stderr)
        return 2
    if not settings.database_url:
        print("DATABASE_URL missing — cannot list preset_voices.", file=sys.stderr)
        return 2

    # Ensure asyncpg driver so create_async_engine can build a real async engine.
    db_url = settings.database_url
    if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        if preset_filter:
            rows = (
                (
                    await conn.execute(
                        text(
                            "SELECT id, name, voice_id FROM preset_voices "
                            "WHERE is_active = TRUE AND id = :pid"
                        ),
                        {"pid": preset_filter},
                    )
                )
                .mappings()
                .all()
            )
        else:
            rows = (
                (
                    await conn.execute(
                        text(
                            "SELECT id, name, voice_id FROM preset_voices "
                            "WHERE is_active = TRUE ORDER BY id"
                        )
                    )
                )
                .mappings()
                .all()
            )
    await engine.dispose()

    if not rows:
        print(f"No active preset rows found (filter={preset_filter!r})", file=sys.stderr)
        return 1

    provider = MiniMaxProvider(
        api_key=settings.minimax_api_key,
        group_id=settings.minimax_group_id or "",
        base_url=settings.minimax_base_url,
    )
    ok_count = 0
    fail_count = 0
    for row in rows:
        ok = await _probe_one(provider, row["id"], row["name"], row["voice_id"])
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    print(f"\nsummary  ok={ok_count}  fail={fail_count}", flush=True)
    return 0 if fail_count == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--id",
        dest="preset_id",
        default=None,
        help="Probe just this preset id (default: all active rows).",
    )
    args = parser.parse_args()
    rc = asyncio.run(_main(args.preset_id))
    sys.exit(rc)


if __name__ == "__main__":
    main()
