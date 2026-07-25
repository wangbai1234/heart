"""上传剧情封面图片到 S3/MinIO 并更新数据库 (2026-07)

匹配逻辑（优先级从高到低）：
  1. 封面文件名 == slug（最可靠：slug 就是原始 .txt 文件名）
  2. 封面文件名 == title（LLM 生成的标题恰好与文件名相同时）

Usage:
    # 检查匹配情况，不实际上传
    python scripts/upload_scenario_covers.py --dry-run

    # 只上传 cover_url 为空的剧情
    python scripts/upload_scenario_covers.py

    # 强制覆盖所有剧情（包含已有 URL 的）
    python scripts/upload_scenario_covers.py --force

    # 自定义封面目录
    python scripts/upload_scenario_covers.py --src /path/to/covers

生产环境用法（设置环境变量后在本地运行，或 SSH 到服务器上运行）：
    DATABASE_URL=postgresql+asyncpg://... \\
    S3_ENDPOINT_URL=https://... \\
    S3_ACCESS_KEY_ID=... \\
    S3_SECRET_ACCESS_KEY=... \\
    S3_BUCKET_NAME=... \\
    S3_PUBLIC_BASE_URL=https://... \\
    python scripts/upload_scenario_covers.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 确保 backend/ 在 import 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)


def _to_webp(png_bytes: bytes, *, quality: int, max_width: int) -> bytes:
    """Convert PNG bytes → resized WebP bytes.

    Covers ship as ~2MB full-res PNGs but render into ≤400px thumbnails, so we
    downscale to `max_width` (keeping aspect) and re-encode as WebP. 102MB of
    PNG → ~5MB of WebP — the dominant first-load speedup. Pillow is imported
    lazily so the non-`--webp` path never needs it.
    """
    import io

    from PIL import Image

    with Image.open(io.BytesIO(png_bytes)) as img:
        # Flatten palette/transparency onto white so WebP is predictable; covers
        # are opaque photos, but guard against P/LA modes just in case.
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


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="上传剧情封面图片到 S3 并更新数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--src",
        default="/Users/wanglixun/Downloads/test",
        help="封面图片目录（默认: %(default)s）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印匹配结果，不实际上传",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已有 cover_url 的剧情",
    )
    parser.add_argument(
        "--webp",
        action="store_true",
        help="上传前把封面转成 WebP 并等比缩放（大幅减小体积，加速首屏）",
    )
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=80,
        help="WebP 质量 0-100（默认: %(default)s）",
    )
    parser.add_argument(
        "--webp-max-width",
        type=int,
        default=800,
        help="缩放后最大宽度（默认: %(default)s，超过才缩放）",
    )
    parser.add_argument(
        "--cover-version",
        default="w1",
        help=(
            "配合 --webp：给 cover_url 追加 ?v=<版本> 以打破浏览器/SW 的 immutable "
            "缓存（默认: %(default)s；下次再优化封面时递增，如 w2）"
        ),
    )
    args = parser.parse_args()

    cover_dir = Path(args.src)
    if not cover_dir.exists():
        print(f"❌ 封面目录不存在: {cover_dir}", file=sys.stderr)
        sys.exit(1)

    # ── 扫描本地封面文件 ─────────────────────────────────────────────
    # key = 文件名 stem（不含扩展名），value = Path 对象
    cover_files: dict[str, Path] = {}
    for f in sorted(cover_dir.glob("*.png")):
        cover_files[f.stem] = f

    if not cover_files:
        print(f"❌ 目录中没有 .png 文件: {cover_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"📁 扫描到 {len(cover_files)} 张封面:")
    for name in cover_files:
        print(f"   {name}.png")

    # ── 加载依赖 ────────────────────────────────────────────────────
    from heart.api.wiring import get_db_session_factory
    from heart.core.config import settings
    from heart.infra.storage import ensure_bucket, upload_file

    if not args.dry_run:
        await ensure_bucket()

    factory = get_db_session_factory()
    if factory is None:
        print("❌ DB session factory 不可用，请检查 DATABASE_URL", file=sys.stderr)
        sys.exit(1)

    async with factory() as db:
        # ── 拉取所有剧情 ────────────────────────────────────────────
        result = await db.execute(
            text("SELECT id, slug, title, cover_url FROM story_scenarios ORDER BY slug")
        )
        scenarios = result.fetchall()
        print(f"\n🗄️  数据库中共 {len(scenarios)} 个剧情\n")

        # ── 匹配：slug 优先，title 兜底 ─────────────────────────────
        #   match_via: "slug" | "title" | None
        matched: list[tuple] = []
        unmatched_covers = set(cover_files.keys())

        for scenario_id, slug, title, cover_url in scenarios:
            if slug in cover_files:
                local_path = cover_files[slug]
                match_via = "slug"
                unmatched_covers.discard(slug)
            elif title in cover_files:
                local_path = cover_files[title]
                match_via = "title"
                unmatched_covers.discard(title)
            else:
                continue
            matched.append((scenario_id, slug, title, cover_url, local_path, match_via))

        # 需要上传的：cover_url 为空，或者 --force 模式下所有匹配的
        need_upload = [
            m for m in matched if not m[3] or args.force
        ]

        # ── 打印匹配报告 ─────────────────────────────────────────────
        print(f"{'=' * 52}")
        print(f"{'DRY RUN — ' if args.dry_run else ''}匹配报告")
        print(f"{'=' * 52}")

        for scenario_id, slug, title, cover_url, local_path, match_via in matched:
            if cover_url and not args.force:
                status = "⏭️  跳过（已有 URL）"
            else:
                status = "⬆️  待上传"
            via = f"[via {match_via}]"
            print(f"{status} {via}")
            print(f"   title : {title}")
            print(f"   slug  : {slug}")
            print(f"   file  : {local_path.name}")
            if cover_url:
                print(f"   old   : {cover_url}")
            if not cover_url or args.force:
                print(f"   → key : scenario_covers/{slug}.png")
            print()

        if unmatched_covers:
            print(f"⚠️  以下封面文件在数据库中没有匹配的剧情（slug 和 title 均不符）：")
            for name in sorted(unmatched_covers):
                print(f"   {name}.png")
            print()

        print(f"{'=' * 52}")
        print(f"匹配: {len(matched)} 个  待上传: {len(need_upload)} 个  无匹配: {len(unmatched_covers)} 个")

        if args.dry_run:
            print("\n💡 去掉 --dry-run 执行实际上传")
            return

        if not need_upload:
            print("\n✅ 没有需要上传的封面（使用 --force 可强制覆盖已有 URL）")
            return

        # ── 实际上传 ─────────────────────────────────────────────────
        print(f"\n开始上传 {len(need_upload)} 个封面...\n")
        uploaded = 0
        failed = 0

        # 当 S3_PUBLIC_BASE_URL 未配置时（内网 MinIO），存后端代理 URL
        # 而不是 http://minio:9000/... 这种浏览器无法访问的内网地址。
        use_proxy = not bool(getattr(settings, "s3_public_base_url", None))
        if use_proxy:
            print("ℹ️  S3_PUBLIC_BASE_URL 未配置，封面 URL 将使用后端代理 /api/story/covers/{slug}\n")

        for scenario_id, slug, title, cover_url, local_path, match_via in need_upload:
            try:
                data = local_path.read_bytes()
                # 保持 key 为 .png（后端代理端点硬编码读 scenario_covers/{slug}.png）；
                # WebP 模式只改字节内容 + content-type，前端凭 content-type 渲染，
                # 无需改后端。体积从 ~2MB 降到 ~100KB。
                key = f"scenario_covers/{slug}.png"
                if args.webp:
                    original = len(data)
                    data = _to_webp(
                        data,
                        quality=args.webp_quality,
                        max_width=args.webp_max_width,
                    )
                    content_type = "image/webp"
                    print(
                        f"   🗜️  {slug}: {original // 1024}KB → {len(data) // 1024}KB (WebP)"
                    )
                else:
                    content_type = "image/png"
                await upload_file(data, key, content_type=content_type)

                # 决定存哪个 URL
                if use_proxy:
                    final_url = f"/api/story/covers/{slug}"
                    # WebP 重传时字节变了但 URL 不变，客户端 immutable 缓存会拿旧图；
                    # 追加 ?v=<版本> 打破浏览器/SW 缓存（query 不影响 FastAPI 路由）。
                    if args.webp:
                        final_url = f"{final_url}?v={args.cover_version}"
                else:
                    from heart.core.config import settings as s
                    base = s.s3_public_base_url.rstrip("/")
                    final_url = f"{base}/{key}"

                await db.execute(
                    text("UPDATE story_scenarios SET cover_url = :url WHERE id = :id"),
                    {"url": final_url, "id": scenario_id},
                )
                await db.commit()

                uploaded += 1
                print(f"✅ [{uploaded}/{len(need_upload)}] {title}")
                print(f"   {final_url}")

            except Exception:
                failed += 1
                logger.exception("cover_upload_failed", title=title, slug=slug)
                print(f"❌ 上传失败: {title}")

        print(f"\n{'=' * 52}")
        print(f"完成！上传成功: {uploaded}  失败: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
