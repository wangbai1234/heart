"""Bulk-import story scenarios from raw ``.txt`` GM prompt packs (SS09, PR6).

Product directive (overrides the plan's "轻度规整"):
    **原文注入** — the ``.txt`` is stored VERBATIM as ``gm_system_prompt``. We do
    NOT normalize, strip meta-instructions, or SFW-sanitize the body. Adult
    content is preserved and gated later via the ``maturity`` tag + age-gate.

What we DO derive is lightweight *card* metadata only, for the Explore grid and
filtering: ``title`` / ``genre`` / ``blurb`` / ``maturity``. These come from a
single cheap-model call over the opening excerpt; they never mutate the prompt.

Idempotency:
    slug = filename stem (stable across runs). ``source_hash`` = sha256 of the
    raw bytes. If a row with the same slug already carries the same
    ``source_hash``, the file is unchanged → skipped WITHOUT an LLM call. Writes
    are ``INSERT ... ON CONFLICT (slug) DO UPDATE`` so re-runs never duplicate.

Scenarios land as ``status='draft'`` by default (human review before publish);
pass ``--publish`` to import straight to ``published``.

Usage (from backend/):
    python scripts/import_scenarios.py --dry-run                # inspect extraction, write nothing
    python scripts/import_scenarios.py                          # import all as draft
    python scripts/import_scenarios.py --publish                # import all as published
    python scripts/import_scenarios.py --only 登仙 --dry-run     # single file by name substring
    python scripts/import_scenarios.py --src /path/to/dir       # custom source dir

Prerequisites: DATABASE_URL set; DB migrated to >= 042; an LLM cheap model
configured (DEEPSEEK_API_KEY etc.) — unless ``--dry-run --no-llm``.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import structlog
from sqlalchemy import text

from heart.core.config import settings
from heart.ss09_story.models import GENRES


def _free_tier_slugs() -> set[str]:
    """The demo slugs free (普通) users may unlock, from config (CSV)."""
    return {s.strip() for s in settings.story_free_tier_slugs.split(",") if s.strip()}

logger = structlog.get_logger(__name__)

DEFAULT_SRC = "/Users/wanglixun/Downloads/剧情设定"

# Only the opening matters for card metadata (title/genre/blurb/maturity); the
# 18禁 / 纯爱 switch and NPC intros live near the top of these packs. Cap the
# excerpt so the classification call stays cheap on 10k+ char files.
_META_EXCERPT_CHARS = 6000

_BLURB_MAX = 40

_METADATA_SYSTEM = (
    "你是一个中文互动剧情剧本的分类助手。只输出卡片元数据，绝不改写、续写或净化正文。"
    "严格返回一个 JSON 对象，不要任何解释或 markdown 代码块。"
)

_METADATA_INSTRUCTION = (
    "根据下面的剧本开头，抽取用于展示卡片的元数据，返回 JSON："
    '{{"title": "简洁标题(≤16字)", "genre": "从固定枚举中选一个", '
    '"blurb": "一句话简介(≤40字，不剧透关键反转)", "maturity": "all_ages 或 adult"}}\n'
    "genre 只能是以下之一：{genres}。无法归类时用「其他」。\n"
    "maturity 判定：出现 18禁/成人/露骨性描写开关或明显色情内容记为 adult，否则 all_ages。\n"
    "默认标题（无更好选择时使用）：{default_title}\n\n"
    "===== 剧本开头 =====\n{excerpt}"
)


@dataclass
class Metadata:
    title: str
    genre: str
    blurb: str
    maturity: str


@dataclass
class ImportResult:
    slug: str
    action: str  # "skipped" | "created" | "updated" | "dry-run" | "error"
    metadata: Optional[Metadata] = None
    detail: str = ""


# ── pure helpers (unit-tested) ──────────────────────────────────────────


def derive_slug(path: Path) -> str:
    """Stable idempotency key from the filename stem (Chinese kept verbatim)."""
    return path.stem.strip()


def compute_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_genre(value: Any) -> str:
    """Snap the model's genre to the fixed enum; anything unknown → 其他."""
    if isinstance(value, str):
        v = value.strip()
        if v in GENRES:
            return v
        # tolerate close variants ("恋爱"→校园恋爱 only on exact; else substring hit)
        for g in GENRES:
            if g != "其他" and (g in v or v in g):
                return g
    return "其他"


def normalize_maturity(value: Any) -> str:
    return "adult" if isinstance(value, str) and value.strip().lower() == "adult" else "all_ages"


def clamp_blurb(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    s = " ".join(value.split()).strip()
    return s[:_BLURB_MAX]


def parse_metadata(raw_json: str, *, default_title: str) -> Metadata:
    """Parse (and defensively normalize) the LLM metadata JSON.

    Robust to code fences / surrounding prose: extracts the first {...} block.
    Any missing/invalid field falls back to a safe default — never raises.
    """
    obj: dict[str, Any] = {}
    if raw_json:
        start, end = raw_json.find("{"), raw_json.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(raw_json[start : end + 1])
                if isinstance(parsed, dict):
                    obj = parsed
            except (TypeError, ValueError):
                obj = {}

    title = obj.get("title")
    title = title.strip() if isinstance(title, str) and title.strip() else default_title
    return Metadata(
        title=title[:64],
        genre=normalize_genre(obj.get("genre")),
        blurb=clamp_blurb(obj.get("blurb")),
        maturity=normalize_maturity(obj.get("maturity")),
    )


def read_text(path: Path) -> str:
    """Read a scenario file, tolerating non-UTF-8 (GBK) encodings."""
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


# ── LLM extraction ──────────────────────────────────────────────────────


async def extract_metadata(router: Any, raw: str, *, default_title: str) -> Metadata:
    """Derive card metadata from the opening excerpt via the cheap model.

    On any LLM/parse failure, degrades to filename-title + 其他 + all_ages so a
    single bad extraction never aborts the batch.
    """
    excerpt = raw[:_META_EXCERPT_CHARS]
    messages = [
        {"role": "system", "content": _METADATA_SYSTEM},
        {
            "role": "user",
            "content": _METADATA_INSTRUCTION.format(
                genres="、".join(GENRES), default_title=default_title, excerpt=excerpt
            ),
        },
    ]
    try:
        out = await router.call_cheap(messages, json_mode=True, agent_name="story_import_meta")
        return parse_metadata(out, default_title=default_title)
    except Exception:
        logger.exception("story_import_metadata_failed", slug=default_title)
        return Metadata(title=default_title, genre="其他", blurb="", maturity="all_ages")


# ── DB upsert ───────────────────────────────────────────────────────────


async def existing_hash(db: Any, slug: str) -> Optional[str]:
    row = await db.execute(
        text("SELECT source_hash FROM story_scenarios WHERE slug = :slug"),
        {"slug": slug},
    )
    return row.scalar_one_or_none()


async def upsert_scenario(
    db: Any,
    *,
    slug: str,
    meta: Metadata,
    gm_system_prompt: str,
    source_hash: str,
    publish: bool,
) -> str:
    """Idempotent upsert. Returns 'created' or 'updated'.

    Only card metadata + the verbatim prompt + hash are written; play_count /
    is_featured / cover_url are preserved on update (curated post-import).
    """
    existed = await existing_hash(db, slug) is not None
    status = "published" if publish else "draft"
    await db.execute(
        text(
            """
            INSERT INTO story_scenarios
                (slug, title, genre, blurb, maturity, gm_system_prompt,
                 source_hash, status, free_tier, updated_at)
            VALUES
                (:slug, :title, :genre, :blurb, :maturity, :prompt,
                 :hash, :status, :free_tier, NOW())
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                genre = EXCLUDED.genre,
                blurb = EXCLUDED.blurb,
                maturity = EXCLUDED.maturity,
                gm_system_prompt = EXCLUDED.gm_system_prompt,
                source_hash = EXCLUDED.source_hash,
                status = EXCLUDED.status,
                free_tier = EXCLUDED.free_tier,
                updated_at = NOW()
            """
        ),
        {
            "slug": slug,
            "title": meta.title,
            "genre": meta.genre,
            "blurb": meta.blurb,
            "maturity": meta.maturity,
            "prompt": gm_system_prompt,
            "hash": source_hash,
            "status": status,
            "free_tier": slug in _free_tier_slugs(),
        },
    )
    return "updated" if existed else "created"


# ── per-file + batch orchestration ──────────────────────────────────────


async def import_one(
    db: Any,
    router: Any,
    path: Path,
    *,
    publish: bool,
    dry_run: bool,
) -> ImportResult:
    slug = derive_slug(path)
    raw = read_text(path)
    if not raw.strip():
        return ImportResult(slug=slug, action="error", detail="empty file")
    source_hash = compute_hash(raw)

    # Unchanged file already imported → skip (no LLM, no write).
    if db is not None:
        prior = await existing_hash(db, slug)
        if prior == source_hash:
            return ImportResult(slug=slug, action="skipped", detail="unchanged")

    meta = await extract_metadata(router, raw, default_title=slug)

    if dry_run:
        return ImportResult(slug=slug, action="dry-run", metadata=meta)

    action = await upsert_scenario(
        db,
        slug=slug,
        meta=meta,
        gm_system_prompt=raw,  # VERBATIM — 原文注入, no normalization
        source_hash=source_hash,
        publish=publish,
    )
    await db.commit()
    return ImportResult(slug=slug, action=action, metadata=meta)


def _select_files(src: Path, only: Optional[str], limit: Optional[int]) -> list[Path]:
    files = sorted(src.glob("*.txt"))
    if only:
        files = [f for f in files if only in f.name]
    if limit:
        files = files[:limit]
    return files


async def _main(
    src: Path, publish: bool, dry_run: bool, only: Optional[str], limit: Optional[int]
) -> None:
    from heart.api.wiring import get_db_session_factory, get_model_router

    files = _select_files(src, only, limit)
    if not files:
        raise SystemExit(f"没有匹配的 .txt 文件：{src} (only={only!r})")

    router = get_model_router()
    if router is None:
        raise SystemExit("ModelRouter 不可用（检查 LLM API key）")

    factory = None if dry_run else get_db_session_factory()
    if not dry_run and factory is None:
        raise SystemExit("DB session factory 不可用（检查 DATABASE_URL）")

    print(f"{'[dry-run] ' if dry_run else ''}导入 {len(files)} 个剧本 ← {src}")
    print(f"状态目标: {'published' if publish else 'draft'}\n")

    results: list[ImportResult] = []

    async def _run(db: Any) -> None:
        for path in files:
            try:
                res = await import_one(db, router, path, publish=publish, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001 — batch resilience: log + continue
                logger.exception("story_import_file_failed", file=path.name)
                res = ImportResult(slug=derive_slug(path), action="error", detail=str(exc))
            results.append(res)
            m = res.metadata
            meta_str = (
                f"  [{m.genre}/{m.maturity}] {m.title} — {m.blurb}" if m else f"  ({res.detail})"
            )
            print(f"{res.action:>8} · {res.slug}\n{meta_str}")

    if dry_run:
        await _run(None)
    else:
        async with factory() as db:  # type: ignore[misc]
            await _run(db)

    # Summary tally.
    tally: dict[str, int] = {}
    for r in results:
        tally[r.action] = tally.get(r.action, 0) + 1
    print("\n=== 汇总 ===")
    for action, n in sorted(tally.items()):
        print(f"  {action}: {n}")
    adult = sum(1 for r in results if r.metadata and r.metadata.maturity == "adult")
    print(f"  adult 分级: {adult}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Import story scenarios (原文注入 + 卡片元数据)")
    ap.add_argument("--src", default=DEFAULT_SRC, help="剧本 .txt 目录")
    ap.add_argument("--publish", action="store_true", help="直接以 published 落库（默认 draft）")
    ap.add_argument("--dry-run", action="store_true", help="只抽取并打印，不写库")
    ap.add_argument("--only", help="仅处理文件名包含该子串的剧本")
    ap.add_argument("--limit", type=int, help="最多处理前 N 个（配合 --dry-run 采样）")
    args = ap.parse_args()

    asyncio.run(_main(Path(args.src), args.publish, args.dry_run, args.only, args.limit))


if __name__ == "__main__":
    main()
