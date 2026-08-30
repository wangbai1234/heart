"""批量导入角色（含竖版封面 + 标签）到发现目录 (2026-07)

这是「运营导入一批角色 + 上传封面」的落地入口，配合 Nimoo 风格发现页。
复用已验证的 draft→SoulSpec 通道（``build_soul_spec_from_draft``），运营只需写一份
简单 manifest（persona / 标签 / 封面文件名 + 可选展示字段），无需手写完整 SoulSpec。

封面按探索页的血泪教训处理：Pillow 转 WebP + 等比缩放（默认 max-width 800 /
quality 80，~2MB PNG → ~100KB），只存 S3 对象 + 短代理 URL，**绝不 base64 内联**。

Manifest 格式（YAML，顶层是列表）::

    - id: xuyan                      # 必填，须匹配 ^[a-z][a-z0-9_]*$，作幂等键
      display_name: { zh: 许砚 }      # 至少一个 zh/ja/en
      gender: female                 # 可选 male|female
      visibility: public             # 可选，默认 public
      tags: [启元赋灵, 女性向, 年上]     # 发现页筛选 chips
      cover: xuyan.png               # --covers 目录下的封面文件（或绝对路径）
      greeting_style: intense        # 可选 warm|cool|playful|reserved|intense
      persona: |                     # 必填 20–1500 字
        ...
      backstory: |                   # 可选 ≤1500 字
        ...
      sliders: { warmth: 0.4, directness: 0.9 }   # 可选，缺省 0.5
      # 以下为档案页展示字段（可选；写入 draft，被 /profile API 读取）
      tagline: 乖，哭出来也很好看呢～            # 「关于TA」一句话
      archetype_label: 审判者·支配俱乐部顶级DOM   # 身份徽标
      one_liner: 西装是铠甲·金丝眼镜是面具·调教室里才是真实
      intro: |                       # 「叙引」正文（缺省用 persona/backstory）
        ...

用法::

    # 预演，不落库不上传
    python scripts/seed_characters.py --manifest chars.yaml --covers ./covers --dry-run

    # 实际导入（生产：先设置 DATABASE_URL / S3_* 环境变量）
    python scripts/seed_characters.py --manifest chars.yaml --covers ./covers

    # 覆盖已存在的角色（重跑：supersede 旧 spec，刷新 tags/cover）
    python scripts/seed_characters.py --manifest chars.yaml --covers ./covers --force

注意：导入后需**重启后端**，SoulRegistry 才会从 soul_specs 加载新角色（display
name / 聊天 prompt）。仅写库不重启时，目录会显示 id 而非中文名。
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import sys
from pathlib import Path

# 确保 backend/ 在 import 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)

_CID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_PRESENTATION_KEYS = (
    "age_range",
    "tagline",
    "archetype_label",
    "one_liner",
    "intro",
    "opening",
    "ui_chrome",
    "profile_blocks",
    "custom_html",
    "premise_card",
    "starter_config",
    "opening_format",
)


def _to_webp(raw: bytes, *, quality: int, max_width: int) -> bytes:
    """PNG/JPEG bytes → 等比缩放后的 WebP bytes（复用探索页封面压缩结论）。"""
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, img).convert("RGB")
        else:
            img = img.convert("RGB")
        if img.width > max_width:
            new_height = round(img.height * max_width / img.width)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=quality, method=6)
        return out.getvalue()


def _build_draft(entry: dict):
    """Manifest 条目 → CharacterDraft（用于生成 SoulSpec）。展示字段不进 model。"""
    from heart.ss01_soul.draft import CharacterDraft, DisplayNameDraft, GreetingStyle, SliderSet

    dn = entry.get("display_name") or {}
    if not isinstance(dn, dict):
        raise ValueError("display_name 必须是含 zh/ja/en 的映射")

    workshop_fields = ("custom_html", "profile_blocks", "premise_card", "starter_config")
    inferred_mode = "workshop" if any(entry.get(field) for field in workshop_fields) else "quick"
    kwargs: dict = {
        "display_name": DisplayNameDraft(zh=dn.get("zh"), ja=dn.get("ja"), en=dn.get("en")),
        "persona": entry["persona"],
        "tags": list(entry.get("tags") or []),
        "creation_mode": entry.get("creation_mode", inferred_mode),
    }
    if entry.get("backstory"):
        kwargs["backstory"] = entry["backstory"]
    for field in ("catchphrases", "speech_samples", "hard_never_user"):
        if field in entry:
            kwargs[field] = entry[field]
    if entry.get("gender") in ("male", "female"):
        kwargs["gender"] = entry["gender"]
    if entry.get("greeting_style"):
        kwargs["greeting_style"] = GreetingStyle(entry["greeting_style"])
    if entry.get("age_range"):
        kwargs["age_range"] = entry["age_range"]
    for field in (
        "opening",
        "intro",
        "tagline",
        "one_liner",
        "archetype_label",
        "ui_chrome",
        "profile_blocks",
        "custom_html",
        "premise_card",
        "starter_config",
        "opening_format",
    ):
        if field in entry and entry[field] is not None:
            kwargs[field] = entry[field]
    if isinstance(entry.get("sliders"), dict):
        kwargs["sliders"] = SliderSet(**entry["sliders"])
    return CharacterDraft(**kwargs)


def _derive_content(draft, character_id: str) -> dict:
    """Deterministic proactive content dict (``CharacterContent`` is a TypedDict).

    Returned as a plain dict so callers can splat it straight into
    ``upsert_content(db, character_id=..., **content)``.
    """
    name = draft.display_name.zh or draft.display_name.ja or draft.display_name.en or character_id
    style_greet = {
        "warm": f"{name}想着你，今天过得怎么样？",
        "cool": f"…{name}在这里。",
        "playful": f"{name}来了！嘿嘿，有没有想我？",
        "reserved": f"{name}注意到今天的你。",
        "intense": f"{name}一直在想你。",
    }
    return {
        "proactive_persona": draft.persona[:200],
        "proactive_templates": [style_greet.get(draft.greeting_style.value, f"{name}来了。")],
        "ritual_morning": f"早安。{name}想和你说声好。",
        "ritual_night": f"晚安。{name}陪着你。",
    }


def _resolve_cover_path(entry: dict, cover_dir: Path) -> Path | None:
    cover = entry.get("cover")
    if not cover:
        return None
    p = Path(cover)
    return p if p.is_absolute() else cover_dir / cover


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="批量导入角色（封面 + 标签）到发现目录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--manifest", required=True, help="角色 manifest（YAML 列表）路径")
    parser.add_argument("--covers", default=".", help="封面图片目录（默认当前目录）")
    parser.add_argument("--dry-run", action="store_true", help="只校验与打印，不上传不落库")
    parser.add_argument("--force", action="store_true", help="覆盖已存在角色（supersede 旧 spec）")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="CHARACTER_ID",
        help="仅处理指定角色；可重复传入，适合安全修复单个第一方角色",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="仅刷新现有角色 active draft 的 custom_html，不改 SoulSpec、封面、标签或其它展示字段",
    )
    parser.add_argument(
        "--skip-covers",
        action="store_true",
        help="完全不处理封面：不校验/不上传，cover_url 置 NULL 走 COALESCE 保留库中现值"
        "（生产刷新开场白等 draft 时用，避免用本地旧封面覆盖线上封面）",
    )
    parser.add_argument("--webp-quality", type=int, default=80, help="WebP 质量（默认 80）")
    parser.add_argument("--webp-max-width", type=int, default=800, help="封面最大宽度（默认 800）")
    parser.add_argument(
        "--cover-version",
        default="c1",
        help="给 cover_url 追加 ?v=<版本> 打破 immutable 缓存（默认 c1；再优化时递增）",
    )
    args = parser.parse_args()

    import yaml

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"❌ manifest 不存在: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    entries = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        print("❌ manifest 顶层必须是非空列表", file=sys.stderr)
        sys.exit(1)
    if args.only:
        requested = set(args.only)
        entries = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") in requested]
        found = {str(entry["id"]) for entry in entries}
        missing = requested - found
        if missing:
            print(f"❌ --only 指定的角色不存在: {', '.join(sorted(missing))}", file=sys.stderr)
            sys.exit(1)

    cover_dir = Path(args.covers)

    # ── 校验（先全量校验，避免半途落库）────────────────────────────────
    prepared: list[dict] = []
    errors: list[str] = []
    for i, raw_entry in enumerate(entries):
        entry = dict(raw_entry) if isinstance(raw_entry, dict) else raw_entry
        if not isinstance(entry, dict):
            errors.append(f"[{i}] 条目必须是映射")
            continue
        cid = entry.get("id")
        if not cid or not _CID_RE.match(str(cid)):
            errors.append(f"[{i}] id 缺失或非法（须 ^[a-z][a-z0-9_]*$）: {cid!r}")
            continue
        if not entry.get("persona"):
            errors.append(f"[{cid}] 缺少 persona")
            continue
        custom_html_file = entry.get("custom_html_file")
        if custom_html_file:
            html_path = manifest_path.parent / str(custom_html_file)
            if not html_path.is_file():
                errors.append(f"[{cid}] HTML 文件不存在: {html_path}")
                continue
            entry["custom_html"] = html_path.read_text(encoding="utf-8")
        try:
            draft = _build_draft(entry)
        except Exception as exc:  # noqa: BLE001 — 校验期把任何构造错误收集起来
            errors.append(f"[{cid}] draft 构造失败: {exc}")
            continue
        cover_path = (
            None if (args.skip_covers or args.html_only) else _resolve_cover_path(entry, cover_dir)
        )
        if cover_path is not None and not cover_path.exists():
            errors.append(f"[{cid}] 封面文件不存在: {cover_path}")
            continue
        prepared.append(
            {
                "id": str(cid),
                "entry": entry,
                "draft": draft,
                "cover_path": cover_path,
                "visibility": entry.get("visibility", "public"),
            }
        )

    print(f"📋 manifest {len(entries)} 条，校验通过 {len(prepared)} 条")
    if errors:
        print("⚠️  以下条目有问题：")
        for e in errors:
            print(f"   - {e}")
    for p in prepared:
        cov = p["cover_path"].name if p["cover_path"] else "（无封面，前端头像派生兜底）"
        print(f"   ✅ {p['id']}  tags={p['entry'].get('tags', [])}  cover={cov}")

    if args.dry_run:
        print("\n💡 去掉 --dry-run 执行实际导入")
        return
    if errors:
        print("\n❌ 存在校验错误，已中止（修正 manifest 后重试）", file=sys.stderr)
        sys.exit(1)
    if not prepared:
        print("\n（无可导入条目）")
        return

    if args.html_only:
        from heart.api.wiring import get_db_session_factory

        factory = get_db_session_factory()
        if factory is None:
            print("❌ DB session factory 不可用，请检查 DATABASE_URL", file=sys.stderr)
            sys.exit(1)

        updated = 0
        async with factory() as db:
            for p in prepared:
                cid = p["id"]
                html = p["entry"].get("custom_html")
                if not html:
                    print(f"⏭️  跳过 {cid}：未提供 custom_html")
                    continue
                result = await db.execute(
                    text(
                        """
                        UPDATE soul_specs
                        SET draft = jsonb_set(
                          COALESCE(draft, '{}'::jsonb),
                          '{custom_html}',
                          CAST(:html_json AS jsonb),
                          true
                        )
                        WHERE character_id = :cid AND status = 'active'
                        """
                    ),
                    {"cid": cid, "html_json": json.dumps(html)},
                )
                if result.rowcount != 1:
                    await db.rollback()
                    print(f"❌ {cid} active SoulSpec 不唯一或不存在，已中止", file=sys.stderr)
                    sys.exit(1)
                updated += 1
            await db.commit()
        print(f"\n完成！仅更新 custom_html：{updated}/{len(prepared)}")
        return

    # ── 依赖 & S3 ───────────────────────────────────────────────────
    from heart.api.wiring import get_db_session_factory
    from heart.core.config import settings
    from heart.infra.storage import ensure_bucket, is_s3_configured, upload_file
    from heart.ss01_soul.content_store import upsert_content
    from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
    from heart.ss01_soul.spec_store import supersede_active

    have_s3 = is_s3_configured()
    if have_s3:
        await ensure_bucket()
    else:
        print("⚠️  未配置对象存储：本次不上传封面（cover_url 置空，前端头像派生兜底）")
    use_proxy = not bool(getattr(settings, "s3_public_base_url", None))

    factory = get_db_session_factory()
    if factory is None:
        print("❌ DB session factory 不可用，请检查 DATABASE_URL", file=sys.stderr)
        sys.exit(1)

    ok = 0
    failed = 0
    async with factory() as db:
        for p in prepared:
            cid = p["id"]
            entry = p["entry"]
            draft = p["draft"]
            try:
                # 存在性检查（幂等）
                existing = await db.execute(
                    text("SELECT owner_user_id FROM characters WHERE id = :cid"),
                    {"cid": cid},
                )
                row = existing.mappings().fetchone()
                if row is not None:
                    if row["owner_user_id"] is not None:
                        print(f"⏭️  跳过 {cid}：已存在且为用户角色（不覆盖 UGC）")
                        continue
                    if not args.force:
                        print(f"⏭️  跳过 {cid}：已存在（--force 可覆盖）")
                        continue

                # 封面：转 WebP → 上传 → cover_url
                cover_url = None
                if p["cover_path"] is not None and have_s3:
                    raw = p["cover_path"].read_bytes()
                    webp = _to_webp(raw, quality=args.webp_quality, max_width=args.webp_max_width)
                    key = f"covers/seed/{cid}.webp"
                    await upload_file(webp, key, content_type="image/webp")
                    if use_proxy:
                        cover_url = (
                            f"/api/profile/cover-file/seed/{cid}.webp?v={args.cover_version}"
                        )
                    else:
                        base = settings.s3_public_base_url.rstrip("/")
                        cover_url = f"{base}/{key}?v={args.cover_version}"
                    print(f"   🗜️  {cid}: {len(raw) // 1024}KB → {len(webp) // 1024}KB (WebP)")

                # SoulSpec + 存储 draft（含展示字段覆盖）
                spec = build_soul_spec_from_draft(draft, character_id=cid)
                draft_dict = draft.model_dump(mode="json")
                if cover_url:
                    draft_dict["cover_url"] = cover_url
                for k in _PRESENTATION_KEYS:
                    if k in entry and entry[k] is not None:
                        draft_dict[k] = entry[k]

                # characters 行（built-in：owner NULL）—— upsert
                await db.execute(
                    text(
                        """
                        INSERT INTO characters
                          (id, owner_user_id, visibility, status, review_status,
                           soul_spec_version, tags, cover_url)
                        VALUES (:id, NULL, :vis, 'active', 'approved',
                                :ver, CAST(:tags AS jsonb), :cover)
                        ON CONFLICT (id) DO UPDATE SET
                          visibility = EXCLUDED.visibility,
                          status = 'active',
                          review_status = 'approved',
                          soul_spec_version = EXCLUDED.soul_spec_version,
                          tags = EXCLUDED.tags,
                          cover_url = COALESCE(EXCLUDED.cover_url, characters.cover_url)
                        """
                    ),
                    {
                        "id": cid,
                        "vis": p["visibility"],
                        "ver": spec.spec_version,
                        "tags": json.dumps(list(entry.get("tags") or [])),
                        "cover": cover_url,
                    },
                )
                if row is not None:
                    await supersede_active(db, cid)
                # 运营导入的目录角色 = 第一方 builtin（owner NULL / public）。
                # Re-running --force for the same built-in version must refresh
                # cover_url / tags / presentation copy, not fail on the
                # (character_id, spec_version) primary key.
                await db.execute(
                    text(
                        """
                        INSERT INTO soul_specs
                          (character_id, spec_version, source, status, spec, draft)
                        VALUES (:cid, :ver, 'builtin', 'active', CAST(:spec AS jsonb), CAST(:draft AS jsonb))
                        ON CONFLICT (character_id, spec_version) DO UPDATE SET
                          source = 'builtin',
                          status = 'active',
                          spec = EXCLUDED.spec,
                          draft = EXCLUDED.draft
                        """
                    ),
                    {
                        "cid": cid,
                        "ver": spec.spec_version,
                        "spec": json.dumps(spec.model_dump(mode="json")),
                        "draft": json.dumps(draft_dict),
                    },
                )
                await upsert_content(db, character_id=cid, **_derive_content(draft, cid))
                await db.commit()
                ok += 1
                print(f"✅ [{ok}] {cid} ({draft.display_name.zh or cid})")
            except Exception:
                failed += 1
                await db.rollback()
                logger.exception("seed_character_failed", character_id=cid)
                print(f"❌ 导入失败: {cid}")

    print(f"\n{'=' * 52}")
    print(f"完成！成功 {ok}  失败 {failed}")
    print("⚠️  记得重启后端，SoulRegistry 才会加载新角色（否则目录显示 id 而非中文名）")


if __name__ == "__main__":
    asyncio.run(main())
