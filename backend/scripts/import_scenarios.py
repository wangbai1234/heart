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

# Extract metadata and player_template from a substantial portion of each file.
# The 玩家自定义区 (player template fields) often appears in the opening, but can
# extend deeper into the file when there are many NPC profiles or detailed options.
# Reading 50%+ of the content ensures we capture all user-fillable fields, avoiding
# the UX issue where missing fields cause the GM to re-ask during gameplay.
# Median file size ~13k chars → 50% ≈ 6500 chars. Use 12000 to cover larger files.
_META_EXCERPT_CHARS = 12000

_BLURB_MAX = 40

_METADATA_SYSTEM = (
    "你是一个中文互动剧情剧本的分类助手。只输出卡片元数据，绝不改写、续写或净化正文。"
    "严格返回一个 JSON 对象，不要任何解释或 markdown 代码块。"
)

_METADATA_INSTRUCTION = (
    "根据下面的剧本开头，抽取用于展示卡片的元数据和玩家开局表单字段，返回 JSON："
    '{{"title": "简洁标题(≤16字)", "genre": "从固定枚举中选一个", '
    '"blurb": "一句话简介(≤40字，不剧透关键反转)", "maturity": "all_ages 或 adult", '
    '"player_template": {{"fields": [字段数组]}}}}\n'
    "genre 只能是以下之一：{genres}。无法归类时用「其他」。\n"
    "maturity 判定：出现 18禁/成人/露骨性描写开关或明显色情内容记为 adult，否则 all_ages。\n"
    "\n"
    "【player_template 提取规则 — 最重要】\n"
    "剧本开头通常有「主控自定义」区，用编号 1. 2. 3.… 列出玩家开局前必须填写/选择的全部项目"
    "（例如：个人信息、纯爱or18禁模式、设定偏好、私设、1v1还是np 等）。\n"
    "你必须把这些编号项**全部**转成表单字段，一个都不能漏——漏掉的项会导致游戏开场时反复追问玩家，体验极差。\n"
    "每个字段格式：\n"
    '{{"key": "英文小写key", "label": "中文显示标签", "type": "text|textarea|select|radio|checkbox", '
    '"required": true|false, "options": ["选项1", "选项2"]}}\n'
    "字段类型选择：\n"
    "- text：短填空（姓名/年龄/星座/MBTI/信息素气味 等单行）。\n"
    "- textarea：长填空（外貌/性格/生平/私设描述 等多行）。\n"
    "- select 或 radio：单选一项（如 性别、纯爱/18禁 模式选择）。二者皆可，模式类用 radio 更直观。\n"
    "- checkbox：多选（凡剧本写「可多选」的设定偏好/玩法偏好，必须用 checkbox 并列出全部 a/b/c/d 选项）。\n"
    "常见个人信息字段：name(姓名,必填), age(年龄), gender(性别,必填), appearance(外貌), "
    "personality(性格), identity(身份), background(生平经历)。\n"
    "特殊字段按剧本原样提取：分化(ABO→options:[Alpha,Beta,Omega])、星座(zodiac)、mbti、"
    "信息素、模式(mode)、设定偏好(preferences)、私设 等。\n"
    "gender 默认 options: [\"男\", \"女\", \"双性\"]；若剧本是 ABO 设定，另出一个 分化 字段。\n"
    "选项要照抄剧本里的原文（含 a/b/c 描述），不要自己发明或精简。含「自定义」选项时也保留。\n"
    "必填项：name、gender，以及剧本明确标注「必填」的项；其余选填。\n"
    "如果剧本开头完全没有玩家自定义区，才返回空 fields: []（会使用默认模版）。\n"
    "默认标题（无更好选择时使用）：{default_title}\n\n"
    "===== 剧本开头 =====\n{excerpt}"
)


@dataclass
class Metadata:
    title: str
    genre: str
    blurb: str
    maturity: str
    player_template: dict[str, Any]  # 玩家信息表单字段定义


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


# Field types the StartRunSheet frontend can render. Anything else degrades to
# text so an unexpected type from the model never produces an unrenderable field.
_VALID_FIELD_TYPES = {"text", "textarea", "select", "radio", "checkbox"}
_CHOICE_TYPES = {"select", "radio", "checkbox"}


def normalize_fields(fields: Any) -> list[dict[str, Any]]:
    """Defensively normalize the LLM's field array into renderable fields.

    Drops fields without a usable key; snaps unknown types to text; ensures
    choice types (select/radio/checkbox) carry a non-empty options list (else
    they degrade to text). Never raises — a bad field is dropped, not fatal.
    """
    if not isinstance(fields, list):
        return []
    out: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for raw in fields:
        if not isinstance(raw, dict):
            continue
        key = raw.get("key")
        if not isinstance(key, str) or not key.strip():
            continue
        key = key.strip()
        if key in seen_keys:
            continue  # dedupe: first field for a key wins
        seen_keys.add(key)

        ftype = raw.get("type")
        ftype = ftype if isinstance(ftype, str) and ftype in _VALID_FIELD_TYPES else "text"

        options_raw = raw.get("options")
        options = [str(o).strip() for o in options_raw if str(o).strip()] if isinstance(options_raw, list) else []
        # A choice field with no options is useless → degrade to a free-text box.
        if ftype in _CHOICE_TYPES and not options:
            ftype = "text"

        label = raw.get("label")
        label = label.strip() if isinstance(label, str) and label.strip() else key

        field: dict[str, Any] = {
            "key": key,
            "label": label,
            "type": ftype,
            "required": bool(raw.get("required", False)),
        }
        if ftype in _CHOICE_TYPES:
            field["options"] = options
        out.append(field)
    return out


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

    # 提取 player_template，规范化每个字段；空/无效 → 空字典（后端用默认模版）
    raw_template = obj.get("player_template", {})
    if isinstance(raw_template, dict) and isinstance(raw_template.get("fields"), list):
        normalized = normalize_fields(raw_template["fields"])
        player_template = {"fields": normalized} if normalized else {}
    else:
        player_template = {}

    return Metadata(
        title=title[:64],
        genre=normalize_genre(obj.get("genre")),
        blurb=clamp_blurb(obj.get("blurb")),
        maturity=normalize_maturity(obj.get("maturity")),
        player_template=player_template,
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
        return Metadata(
            title=default_title, genre="其他", blurb="", maturity="all_ages", player_template={}
        )


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

    Only card metadata + the verbatim prompt + hash + player_template are written;
    play_count / is_featured / cover_url are preserved on update (curated post-import).
    """
    existed = await existing_hash(db, slug) is not None
    status = "published" if publish else "draft"
    # player_template_json: 空字典 → NULL（后端用默认模版）；有字段 → JSON
    template_json = json.dumps(meta.player_template, ensure_ascii=False) if meta.player_template else None
    await db.execute(
        text(
            """
            INSERT INTO story_scenarios
                (slug, title, genre, blurb, maturity, gm_system_prompt,
                 player_template_json, source_hash, status, free_tier, updated_at)
            VALUES
                (:slug, :title, :genre, :blurb, :maturity, :prompt,
                 CAST(:template AS JSONB), :hash, :status, :free_tier, NOW())
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                genre = EXCLUDED.genre,
                blurb = EXCLUDED.blurb,
                maturity = EXCLUDED.maturity,
                gm_system_prompt = EXCLUDED.gm_system_prompt,
                player_template_json = EXCLUDED.player_template_json,
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
            "template": template_json,
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
    force: bool = False,
) -> ImportResult:
    slug = derive_slug(path)
    raw = read_text(path)
    if not raw.strip():
        return ImportResult(slug=slug, action="error", detail="empty file")
    source_hash = compute_hash(raw)

    # Unchanged file already imported → skip (no LLM, no write), unless --force.
    if db is not None and not force:
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
    src: Path, publish: bool, dry_run: bool, only: Optional[str], limit: Optional[int], force: bool
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
                res = await import_one(db, router, path, publish=publish, dry_run=dry_run, force=force)
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
    ap.add_argument("--force", action="store_true", help="强制重新提取元数据（即使 source_hash 未变）")
    args = ap.parse_args()

    asyncio.run(_main(Path(args.src), args.publish, args.dry_run, args.only, args.limit, args.force))


if __name__ == "__main__":
    main()
