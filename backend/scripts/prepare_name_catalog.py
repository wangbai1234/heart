"""Create a local-only multilingual role-name preview.

This batch deliberately changes only presentation names. Source characters and
historical conversations are never updated. The generated rows are editorial
previews: their source-language body is retained until a later localization
pass and their audit status remains ``pending_owner_review``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from text_unidecode import unidecode

from heart.core.config import settings
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss01_soul.spec_store import insert_spec

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ("en", "ja", "ko")

JA_FAMILY = (
    "佐藤",
    "鈴木",
    "高橋",
    "田中",
    "伊藤",
    "渡辺",
    "山本",
    "中村",
    "小林",
    "加藤",
    "吉田",
    "山田",
    "佐々木",
    "山口",
    "松本",
    "井上",
    "木村",
    "林",
    "清水",
    "斎藤",
    "森",
    "池田",
    "橋本",
    "阿部",
    "石川",
    "山下",
    "中島",
    "石井",
    "小川",
    "前田",
    "岡田",
    "藤田",
    "後藤",
    "長谷川",
    "村上",
    "近藤",
    "石田",
    "坂本",
    "遠藤",
    "青木",
    "藤井",
    "西村",
    "福田",
    "太田",
    "三浦",
    "藤原",
    "岡本",
    "松田",
    "中川",
    "中野",
    "黒川",
    "神谷",
    "白石",
    "朝倉",
    "水瀬",
    "一ノ瀬",
    "桐生",
    "久我",
    "相沢",
    "瀬戸",
)
JA_MALE = (
    "蓮",
    "律",
    "湊",
    "悠真",
    "蒼",
    "樹",
    "陽向",
    "奏",
    "岳",
    "慧",
    "伊織",
    "直哉",
    "颯太",
    "朔",
    "晴臣",
    "玲",
    "恭平",
    "千隼",
    "郁",
    "冬真",
    "景",
    "新",
    "拓海",
)
JA_FEMALE = (
    "凛",
    "葵",
    "結衣",
    "美月",
    "花音",
    "詩織",
    "紗季",
    "雫",
    "澪",
    "千夏",
    "琴音",
    "陽菜",
    "真央",
    "楓",
    "灯",
    "すみれ",
    "莉子",
    "雪乃",
    "遥",
    "七海",
    "奏",
)
JA_NEUTRAL = ("ひかり", "つばさ", "あおい", "なぎ", "かえで", "しおん", "そら", "いぶき")

KO_FAMILY = (
    "김",
    "이",
    "박",
    "최",
    "정",
    "강",
    "조",
    "윤",
    "장",
    "임",
    "한",
    "오",
    "서",
    "신",
    "권",
    "황",
    "안",
    "송",
    "전",
    "홍",
    "유",
    "문",
    "양",
    "손",
    "배",
    "백",
    "허",
    "남",
    "심",
    "노",
    "하",
    "곽",
    "성",
    "차",
    "주",
    "우",
    "구",
    "민",
    "류",
    "진",
    "강",
)
KO_MALE = (
    "도윤",
    "서준",
    "지훈",
    "현우",
    "민재",
    "시우",
    "준혁",
    "태윤",
    "건우",
    "우진",
    "윤재",
    "현준",
    "재현",
    "승현",
    "지호",
    "도현",
    "정우",
    "시온",
    "태민",
    "주원",
    "하준",
    "은호",
)
KO_FEMALE = (
    "서윤",
    "지우",
    "수아",
    "하은",
    "예은",
    "채원",
    "다은",
    "유나",
    "서연",
    "나연",
    "민서",
    "지민",
    "소윤",
    "하린",
    "유진",
    "아린",
    "은채",
    "채은",
    "다현",
    "보민",
    "가은",
    "수빈",
)
KO_NEUTRAL = ("하늘", "가람", "다온", "시온", "이든", "한결", "새봄", "라온")

EN_MALE = (
    "Julian",
    "Elliot",
    "Theo",
    "Adrian",
    "Milo",
    "Soren",
    "Noah",
    "Elias",
    "Luca",
    "Leon",
    "Felix",
    "Jasper",
    "Mason",
    "Dorian",
    "Silas",
    "Miles",
    "Arthur",
    "Caleb",
    "Everett",
    "Nolan",
    "Roman",
    "Hugo",
    "Emmett",
    "Graham",
    "Wesley",
    "Bennett",
    "August",
    "Oscar",
    "Simon",
    "Declan",
)
EN_FEMALE = (
    "Claire",
    "Iris",
    "Maya",
    "Elena",
    "Nora",
    "Violet",
    "Celine",
    "Mina",
    "Hazel",
    "Naomi",
    "Amelia",
    "Sienna",
    "Lydia",
    "Freya",
    "Margot",
    "Elise",
    "Audrey",
    "Celeste",
    "Tessa",
    "Maeve",
    "Willow",
    "Rosalie",
    "Lena",
    "Dahlia",
    "Isla",
    "Serena",
    "Wren",
    "June",
    "Marlowe",
    "Eva",
)
EN_NEUTRAL = (
    "Avery",
    "Rowan",
    "Morgan",
    "Cameron",
    "Remy",
    "Quinn",
    "Sage",
    "River",
    "Skyler",
    "Ellis",
)
EN_SURNAME = (
    "Bennett",
    "Mercer",
    "Hart",
    "Hayes",
    "Wilder",
    "Foster",
    "Vale",
    "Sterling",
    "Reed",
    "Monroe",
    "Parker",
    "Ellis",
    "West",
    "Arden",
    "Marlowe",
    "Bell",
    "Carter",
    "Lane",
    "Pierce",
    "Sloane",
    "Morrison",
    "Brooks",
    "Everett",
    "Sinclair",
    "Holloway",
    "Quinn",
    "Wells",
    "Sawyer",
    "Rhodes",
    "Lennox",
)
EN_GROUP = (
    "Afterglow Ensemble",
    "Open Horizons",
    "Silverline House",
    "Northstar Circle",
    "Velvet Company",
    "Moonlit Collective",
    "Blue Hour Society",
    "Wildflower Company",
    "Hearthlight House",
    "Daybreak Ensemble",
    "Crescent Circle",
    "Skylark Collective",
    "Golden Hour Company",
    "Rainfall House",
    "Starlane Ensemble",
    "Westwind Society",
    "Kindred Circle",
    "Cloudline Company",
    "Sundown Collective",
    "Lighthouse Ensemble",
    "Rosewood House",
    "New Moon Circle",
    "Evergreen Company",
    "Bluebell Society",
)
JA_GROUP = (
    "青羽楽団",
    "星影座",
    "月虹カンパニー",
    "白夜サークル",
    "雨音アンサンブル",
    "蒼穹ハウス",
    "花灯り座",
    "銀河サークル",
    "風待ちカンパニー",
    "朝凪アンサンブル",
    "木漏れ日座",
    "夜明けハウス",
    "薄明サークル",
    "水鏡アンサンブル",
    "雪月カンパニー",
    "流星座",
    "青空ハウス",
    "灯台サークル",
    "春風アンサンブル",
    "星屑カンパニー",
    "夕映え座",
    "雲間ハウス",
    "花霞サークル",
    "遠雷アンサンブル",
)
KO_GROUP = (
    "청우 앙상블",
    "별빛 극단",
    "무지개 하우스",
    "새벽 서클",
    "달무리 앙상블",
    "푸른별 컴퍼니",
    "꽃비 서클",
    "은하 극단",
    "바람결 하우스",
    "아침노을 앙상블",
    "나무그늘 컴퍼니",
    "여명 서클",
    "물안개 극단",
    "눈꽃 하우스",
    "유성 앙상블",
    "푸른하늘 서클",
    "등대 컴퍼니",
    "봄바람 극단",
    "별가루 하우스",
    "저녁노을 앙상블",
    "구름숲 서클",
    "꽃안개 컴퍼니",
    "먼바다 극단",
    "새달 하우스",
)

ASCII_NAMES = {
    "k": {"en": "K", "ja": "ケイ", "ko": "케이"},
    "zane": {"en": "Zane", "ja": "ゼイン", "ko": "제인"},
    "vito rosetti": {"en": "Vito Rosetti", "ja": "ヴィート・ロゼッティ", "ko": "비토 로세티"},
    "free muse": {"en": "Free Muse", "ja": "フリーミューズ", "ko": "프리 뮤즈"},
    "qingyu band": {"en": "Qingyu Ensemble", "ja": "青羽楽団", "ko": "청우 앙상블"},
    "linyuan manor": {"en": "Linyuan House", "ja": "臨淵館", "ko": "림연 저택"},
}
SOURCE_NAME_OVERRIDES = {
    "vito_rosetti": {"en": "Vito Rosetti", "ja": "ヴィート・ロゼッティ", "ko": "비토 로세티"},
    "xize": {"en": "Cecil Vale", "ja": "セシル・ヴェイル", "ko": "세실 베일"},
    "elias_vayne": {"en": "Elias Vayne", "ja": "イライアス・ヴェイン", "ko": "엘리아스 베인"},
}


def stable_index(source_id: str, locale: str, size: int) -> int:
    return int(hashlib.sha256(f"{source_id}:{locale}".encode()).hexdigest()[:12], 16) % size


def source_name(draft: dict, spec: dict, source_id: str) -> str:
    raw = draft.get("display_name") or spec.get("display_name") or {}
    if isinstance(raw, dict):
        return str(raw.get("zh") or raw.get("ja") or raw.get("ko") or raw.get("en") or source_id)
    return str(raw or source_id)


def gender_of(draft: dict) -> str | None:
    value = draft.get("gender")
    return value if value in {"male", "female"} else None


def is_group(name: str, draft: dict, tagline: str = "") -> bool:
    text = f"{name} {tagline} {draft.get('cast_type', '')}"
    return any(
        token in text.casefold() for token in ("乐队", "庄园", "多人", "band", "manor", "ensemble")
    )


def clean_latin(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9' -]+", " ", value).strip()
    return re.sub(r"\s+", " ", value)


def name_for(source_id: str, locale: str, original: str, gender: str | None, group: bool) -> str:
    if source_id in SOURCE_NAME_OVERRIDES:
        return SOURCE_NAME_OVERRIDES[source_id][locale]
    key = original.strip().casefold()
    if key in ASCII_NAMES:
        return ASCII_NAMES[key][locale]
    latin = clean_latin(unidecode(original)).title()
    if locale == "en":
        if group:
            return EN_GROUP[stable_index(source_id, locale, len(EN_GROUP))]
        parts = latin.split()
        if parts and not re.search(r"[\u3400-\u9fff]", original):
            return " ".join(parts)[:40]
        pool = EN_MALE if gender == "male" else EN_FEMALE if gender == "female" else EN_NEUTRAL
        given = pool[stable_index(source_id, locale, len(pool))]
        surname = EN_SURNAME[stable_index(source_id, locale + "s", len(EN_SURNAME))]
        return f"{given} {surname}"[:40]
    if locale == "ja":
        if group:
            return f"{('青羽' if '乐队' in original else '臨淵')}" + (
                "楽団" if "乐队" in original else "館"
            )
        pool = JA_MALE if gender == "male" else JA_FEMALE if gender == "female" else JA_NEUTRAL
        return f"{JA_FAMILY[stable_index(source_id, locale + 'f', len(JA_FAMILY))]} {pool[stable_index(source_id, locale, len(pool))]}"
    if group:
        return f"{('청우' if '乐队' in original else '림연')}" + (
            " 앙상블" if "乐队" in original else " 저택"
        )
    pool = KO_MALE if gender == "male" else KO_FEMALE if gender == "female" else KO_NEUTRAL
    return f"{KO_FAMILY[stable_index(source_id, locale + 'f', len(KO_FAMILY))]}{pool[stable_index(source_id, locale, len(pool))]}"


def alternatives_for(source_id: str, locale: str, original: str, gender: str | None, group: bool):
    """Return collision alternatives without appending unnatural numeric suffixes."""
    if group:
        pool = {"en": EN_GROUP, "ja": JA_GROUP, "ko": KO_GROUP}[locale]
        start = stable_index(source_id, locale, len(pool))
        return [pool[(start + offset) % len(pool)] for offset in range(len(pool))]
    if locale == "en":
        first_names = (
            EN_MALE if gender == "male" else EN_FEMALE if gender == "female" else EN_NEUTRAL
        )
        pairs = [f"{first} {last}" for first in first_names for last in EN_SURNAME]
        start = stable_index(source_id, locale, len(pairs))
    elif locale == "ja":
        first_names = (
            JA_MALE if gender == "male" else JA_FEMALE if gender == "female" else JA_NEUTRAL
        )
        pairs = [f"{family} {given}" for family in JA_FAMILY for given in first_names]
        start = stable_index(source_id, locale, len(pairs))
    else:
        first_names = (
            KO_MALE if gender == "male" else KO_FEMALE if gender == "female" else KO_NEUTRAL
        )
        pairs = [f"{family}{given}" for family in KO_FAMILY for given in first_names]
        start = stable_index(source_id, locale, len(pairs))
    return [pairs[(start + offset) % len(pairs)] for offset in range(len(pairs))]


def load_existing_names() -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for item in json.loads((ROOT / "docs/international/launch_catalog.json").read_text()):
        result[(item["source_character_id"], item["locale"])] = item["name"]
    return result


def build_plan(sources: list[dict]) -> list[dict]:
    existing = load_existing_names()
    used = {locale: set() for locale in LOCALES}
    plan: list[dict] = []
    for source in sources:
        draft = source["draft"] or {}
        spec = source["spec"] or {}
        original = source_name(draft, spec, source["id"])
        group = is_group(original, draft, draft.get("tagline", ""))
        gender = gender_of(draft)
        for locale in LOCALES:
            name = existing.get((source["id"], locale)) or name_for(
                source["id"], locale, original, gender, group
            )
            if name.casefold() in used[locale]:
                name = next(
                    (
                        candidate
                        for candidate in alternatives_for(
                            source["id"], locale, original, gender, group
                        )
                        if candidate.casefold() not in used[locale]
                    ),
                    None,
                )
                if name is None:
                    raise ValueError(
                        f"No unique name candidates remain for {source['id']} ({locale})"
                    )
            used[locale].add(name.casefold())
            plan.append(
                {
                    "source_character_id": source["id"],
                    "locale": locale,
                    "character_id": f"launch_{locale}_{source['id']}",
                    "source_name": original,
                    "name": name,
                    "gender": gender,
                    "group": group,
                    "status": "pending_owner_review",
                    "name_method": "curated_existing"
                    if (source["id"], locale) in existing
                    else "deterministic_name_seed",
                }
            )
    return plan


def guarded_engine():
    url = make_url(settings.database_url)
    if url.host not in {"localhost", "127.0.0.1"} or url.database != "heart_review":
        raise SystemExit("Only loopback heart_review is permitted.")
    return create_async_engine(settings.database_url)


async def apply(plan_path: Path, source_path: Path, manifest_path: Path) -> None:
    plan = json.loads(plan_path.read_text())
    sources = {row["id"]: row for row in json.loads(source_path.read_text())}
    engine = guarded_engine()
    manifest: list[dict] = []
    try:
        async with engine.begin() as db:
            await db.execute(
                text("""CREATE TABLE IF NOT EXISTS local_review.multilingual_name_adaptations (
                character_id TEXT PRIMARY KEY, source_character_id TEXT NOT NULL, locale TEXT NOT NULL,
                source_name TEXT NOT NULL, localized_name TEXT NOT NULL, source_snapshot JSONB NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_owner_review', method TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(source_character_id, locale))""")
            )
            for item in plan:
                source = sources[item["source_character_id"]]
                draft_data = dict(source["draft"] or {})
                original_name = source_name(draft_data, source["spec"], source["id"])
                display = {item["locale"]: item["name"]}
                draft_data["display_name"] = display
                draft_data["locale"] = item["locale"]
                draft_data["response_language"] = item["locale"]
                draft_data["visibility"] = source["visibility"]
                draft_data["creation_mode"] = "workshop"
                draft = CharacterDraft.model_validate(draft_data)
                cid = item["character_id"]
                # Existing hand-edited launch rows are preserved byte-for-byte.
                existing = await db.execute(
                    text("SELECT id FROM characters WHERE id=:id"), {"id": cid}
                )
                if existing.scalar_one_or_none() is None:
                    spec = build_soul_spec_from_draft(draft, character_id=cid)
                    await db.execute(
                        text("""INSERT INTO characters
                        (id, owner_user_id, visibility, status, soul_spec_version, tags, cover_url, review_status)
                        VALUES (:id, :owner, :visibility, 'active', :version, CAST(:tags AS jsonb), :cover, 'approved')"""),
                        {
                            "id": cid,
                            "owner": source["owner_user_id"],
                            "visibility": source["visibility"],
                            "version": spec.spec_version,
                            "tags": json.dumps(draft.tags, ensure_ascii=False),
                            "cover": draft.cover_url,
                        },
                    )
                    await insert_spec(
                        db,
                        character_id=cid,
                        spec_version=spec.spec_version,
                        spec=spec.model_dump(mode="json"),
                        draft=draft.model_dump(mode="json"),
                    )
                else:
                    # Keep variants under the original creator and preserve the
                    # source's public/link-only setting in local review.
                    await db.execute(
                        text(
                            "UPDATE characters SET owner_user_id=:owner, visibility=:visibility WHERE id=:id"
                        ),
                        {
                            "id": cid,
                            "owner": source["owner_user_id"],
                            "visibility": source["visibility"],
                        },
                    )
                    if item["name_method"] != "curated_existing":
                        spec = build_soul_spec_from_draft(draft, character_id=cid)
                        await db.execute(
                            text("""UPDATE soul_specs SET spec=CAST(:spec AS jsonb), draft=CAST(:draft AS jsonb)
                            WHERE character_id=:id AND status='active'"""),
                            {
                                "id": cid,
                                "spec": json.dumps(
                                    spec.model_dump(mode="json"), ensure_ascii=False
                                ),
                                "draft": draft.model_dump_json(),
                            },
                        )
                await db.execute(
                    text("""INSERT INTO local_review.multilingual_name_adaptations
                    (character_id, source_character_id, locale, source_name, localized_name, source_snapshot, status, method)
                    VALUES (:id, :source, :locale, :source_name, :localized_name, CAST(:snapshot AS jsonb), :status, :method)
                    ON CONFLICT (character_id) DO UPDATE SET localized_name=EXCLUDED.localized_name, status=EXCLUDED.status"""),
                    {
                        "id": cid,
                        "source": source["id"],
                        "locale": item["locale"],
                        "source_name": original_name,
                        "localized_name": item["name"],
                        "snapshot": json.dumps(source, ensure_ascii=False, default=str),
                        "status": "pending_owner_review",
                        "method": item["name_method"],
                    },
                )
                manifest.append({**item, "url": f"http://127.0.0.1:55173/character/{cid}"})
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sources = json.loads(args.sources.read_text())
    plan = build_plan(sources)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    print(f"planned {len(plan)} names for {len(sources)} source roles")
    if args.apply:
        import asyncio

        asyncio.run(apply(args.plan, args.sources, args.manifest))
        print(f"applied {len(plan)} local-only name previews")


if __name__ == "__main__":
    main()
