from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageChops, ImageFilter
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "web" / "design" / "source"
ASSETS = ROOT / "assets"


@dataclass(frozen=True)
class AssetSpec:
    name: str
    source: str
    box: tuple[int, int, int, int]
    out: str
    kind: str
    description: str
    transform: str


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def open_source(rel_path: str) -> Image.Image:
    return Image.open(SOURCE / rel_path).convert("RGBA")


def crop(im: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    return im.crop(box)


def tight_bbox_from_background(
    image: Image.Image, threshold: int = 24
) -> tuple[int, int, int, int] | None:
    rgb = image.convert("RGB")
    samples = [
        rgb.getpixel((0, 0)),
        rgb.getpixel((rgb.width - 1, 0)),
        rgb.getpixel((0, rgb.height - 1)),
        rgb.getpixel((rgb.width - 1, rgb.height - 1)),
    ]
    avg = tuple(sum(channel) // len(samples) for channel in zip(*samples))
    bg = Image.new("RGB", rgb.size, avg)
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda px: 255 if px > threshold else 0)
    return mask.getbbox()


def flood_extract_foreground(
    image: Image.Image, threshold: int = 22, dilate: int = 2
) -> Image.Image:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    height, width = rgb.shape[:2]
    samples = np.array(
        [rgb[0, 0], rgb[0, width - 1], rgb[height - 1, 0], rgb[height - 1, width - 1]],
        dtype=np.int16,
    )
    background = samples.mean(axis=0)
    distance = np.sqrt(((rgb - background) ** 2).sum(axis=-1))
    background_candidate = distance < threshold

    visited = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        for y in (0, height - 1):
            if background_candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if background_candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))

    while queue:
        y, x = queue.popleft()
        for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if (
                0 <= next_y < height
                and 0 <= next_x < width
                and background_candidate[next_y, next_x]
                and not visited[next_y, next_x]
            ):
                visited[next_y, next_x] = True
                queue.append((next_y, next_x))

    foreground = ~visited
    for _ in range(dilate):
        padded = np.pad(foreground, 1)
        foreground = (
            padded[1:-1, 1:-1]
            | padded[:-2, 1:-1]
            | padded[2:, 1:-1]
            | padded[1:-1, :-2]
            | padded[1:-1, 2:]
            | padded[:-2, :-2]
            | padded[:-2, 2:]
            | padded[2:, :-2]
            | padded[2:, 2:]
        )

    alpha = Image.fromarray((foreground * 255).astype(np.uint8), "L")
    result = image.copy()
    result.putalpha(alpha)
    bbox = result.getbbox()
    return result.crop(bbox) if bbox else result


def circle_avatar(image: Image.Image, glow_padding: int = 12) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return image
    x0, y0, x1, y1 = bbox
    bbox = (
        max(0, x0 - glow_padding),
        max(0, y0 - glow_padding),
        min(image.width, x1 + glow_padding),
        min(image.height, y1 + glow_padding),
    )
    return image.crop(bbox)


def circular_crop(image: Image.Image) -> Image.Image:
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    mask = Image.new("L", (side, side), 0)
    # Pillow ellipse antialiasing via blur keeps the glow edge softer.
    from PIL import ImageDraw

    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, side - 1, side - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.25))
    rgba = image.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def crop_box(spec: AssetSpec) -> Image.Image:
    return crop(open_source(spec.source), spec.box)


def transform(spec: AssetSpec) -> Image.Image:
    image = crop_box(spec)
    if spec.transform == "crop":
        return image
    if spec.transform == "crop_webp":
        return image
    if spec.transform == "circle_avatar":
        return circular_crop(image)
    if spec.transform == "flood_extract":
        threshold = 22
        dilate = 2
        if "gift_box" in spec.name:
            threshold = 18
            dilate = 1
        if "starburst" in spec.name:
            threshold = 10
            dilate = 0
        return flood_extract_foreground(image, threshold=threshold, dilate=dilate)
    raise ValueError(f"Unknown transform: {spec.transform}")


SPECS: list[AssetSpec] = [
    AssetSpec(
        name="character_shenwuyue_avatar",
        source="phase2_screens/12_character.png",
        box=(63, 527, 362, 826),
        out="characters/character_shenwuyue_avatar.png",
        kind="character",
        description="Large circular avatar with the original violet aura.",
        transform="circle_avatar",
    ),
    AssetSpec(
        name="character_taolesi_avatar",
        source="phase2_screens/12_character.png",
        box=(62, 931, 362, 1231),
        out="characters/character_taolesi_avatar.png",
        kind="character",
        description="Large circular avatar with the original blue aura.",
        transform="circle_avatar",
    ),
    AssetSpec(
        name="character_youyou_avatar",
        source="phase2_screens/10_chat_light.png",
        box=(110, 57, 251, 198),
        out="characters/character_youyou_avatar.png",
        kind="character",
        description="Small circular chat avatar extracted from the light chat screen.",
        transform="circle_avatar",
    ),
    AssetSpec(
        name="illustration_heart_emblem",
        source="phase1_foundations/07_app_icon.png",
        box=(58, 352, 578, 840),
        out="illustrations/illustration_heart_emblem.png",
        kind="illustration",
        description="Primary floating heart illustration on transparent background.",
        transform="flood_extract",
    ),
    AssetSpec(
        name="illustration_gift_box",
        source="phase2_screens/15_redeem.png",
        box=(404, 176, 676, 392),
        out="illustrations/illustration_gift_box.png",
        kind="illustration",
        description="Redeem-page gift box illustration with ribbon and soft glow.",
        transform="flood_extract",
    ),
    AssetSpec(
        name="background_login_hero",
        source="phase2_screens/14_login.png",
        box=(0, 95, 1024, 542),
        out="backgrounds/background_login_hero.webp",
        kind="background",
        description="Wide fantasy sky hero used on the login screen.",
        transform="crop_webp",
    ),
    AssetSpec(
        name="background_character_hero",
        source="phase2_screens/12_character.png",
        box=(0, 157, 1024, 430),
        out="backgrounds/background_character_hero.webp",
        kind="background",
        description="Character selection sky banner with centered heart emblem.",
        transform="crop_webp",
    ),
    AssetSpec(
        name="background_castle_garden",
        source="phase1_foundations/01_style_tile.png",
        box=(0, 1350, 1024, 1488),
        out="backgrounds/background_castle_garden.webp",
        kind="background",
        description="Pastel castle-and-garden strip illustration from the style tile.",
        transform="crop_webp",
    ),
    AssetSpec(
        name="illustration_empty_state_heart_cloud",
        source="phase3_states/18_state_empty.png",
        box=(390, 160, 810, 385),
        out="illustrations/illustration_empty_state_heart_cloud.webp",
        kind="illustration",
        description="Heart-over-cloud cluster from the empty chat state.",
        transform="crop_webp",
    ),
    AssetSpec(
        name="effect_starburst_pink",
        source="phase2_screens/14_login.png",
        box=(442, 66, 502, 126),
        out="effects/effect_starburst_pink.png",
        kind="effect",
        description="Single glowing starburst for lightweight overlays.",
        transform="flood_extract",
    ),
    AssetSpec(
        name="effect_glow_heart_soft",
        source="phase1_foundations/07_app_icon.png",
        box=(18, 290, 628, 915),
        out="effects/effect_glow_heart_soft.png",
        kind="effect",
        description="Heart aura with extra glow padding for overlay use.",
        transform="flood_extract",
    ),
]


def save_image(image: Image.Image, path: Path) -> None:
    ensure_parent(path)
    if path.suffix.lower() == ".webp":
        image.convert("RGB").save(path, quality=96, method=6)
    else:
        image.save(path)


def export_assets() -> list[dict[str, str]]:
    manifest: list[dict[str, str]] = []
    for spec in SPECS:
        image = transform(spec)
        path = ASSETS / spec.out
        save_image(image, path)
        manifest.append(
            {
                "name": spec.name,
                "kind": spec.kind,
                "path": str(path.relative_to(ROOT)),
                "source": str((SOURCE / spec.source).relative_to(ROOT)),
                "description": spec.description,
                "transform": spec.transform,
            }
        )
    return manifest


def cleanup_previous_exports() -> None:
    for folder_name in [
        "characters",
        "backgrounds",
        "illustrations",
        "effects",
        "textures",
        "decorations",
    ]:
        folder = ASSETS / folder_name
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file():
                path.unlink()

    manifest_path = ASSETS / "_meta" / "manifest.json"
    if not manifest_path.exists():
        return
    try:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    for row in previous:
        rel_path = row.get("path")
        if not rel_path:
            continue
        path = ROOT / rel_path
        if path.exists():
            path.unlink()


def write_manifest(rows: Iterable[dict[str, str]]) -> None:
    manifest_path = ASSETS / "_meta" / "manifest.json"
    ensure_parent(manifest_path)
    manifest_path.write_text(
        json.dumps(list(rows), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    cleanup_previous_exports()
    rows = export_assets()
    write_manifest(rows)
    print(f"Exported {len(rows)} assets to {ASSETS}")
