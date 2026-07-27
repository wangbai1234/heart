"""批量导入内置角色：创建 Soul Spec YAML + 数据库条目 + 复制头像。

用法：
    cd /Users/wanglixun/heart
    python scripts/import_builtin_characters.py --dry-run   # 预览
    python scripts/import_builtin_characters.py             # 执行
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# ── 角色映射：pinyin_id → (中文名, 简介) ──────────────────────────────
CHARACTER_MAP: dict[str, tuple[str, str]] = {
    "lu_chen": ("陆辰", "温柔深情的豪门继承人，外表冷漠内心炽热。"),
    "yun_zhi": ("云芝", "清冷出尘的修仙天才，剑道通神却不懂人心。"),
    "su_yueyao": ("苏月瑶", "明媚如月的古风少女，一笑倾城再笑倾国。"),
    "murong_jin": ("慕容锦", "腹黑霸道的世家公子，掌控一切却掌控不了自己的心。"),
    "su_wan": ("苏婉", "温婉如水的大家闺秀，藏着不为人知的秘密。"),
    "xuan_ye": ("玄夜", "神秘莫测的暗夜行者，亦正亦邪令人捉摸不透。"),
    "bai_zhi": ("白枝", "天真烂漫的精灵少女，与自然有着神秘的联系。"),
    "mu_beihan": ("慕北寒", "冷峻孤傲的北境之王，只为一人温柔。"),
    "ye_lan": ("叶兰", "知性优雅的都市丽人，职场上雷厉风行私下却意外软萌。"),
    "bai_qinghuan": ("白清欢", "风流倜傥的江湖侠客，剑胆琴心潇洒不羁。"),
    "jiang_ye": ("江夜", "沉默寡言的天才医生，手术刀下救万人却救不了自己。"),
    "shen_guhong": ("沈孤鸿", "孤高冷傲的剑修，一生只为追求剑道极致。"),
    "pei_jue": ("裴珏", "表面纨绔实则深藏不露的贵公子。"),
    "jiang_yanzhou": ("姜衍舟", "温润如玉的世家公子，举手投足皆是风雅。"),
    "luo_yin": ("洛吟", "才华横溢的诗人，用文字编织最动人的情话。"),
    "free_muse": ("缪斯", "自由奔放的艺术家，灵感如泉涌永不枯竭。"),
    "shi_yue": ("石月", "坚韧不拔的女将军，沙场上所向披靡。"),
    "gu_xingmian": ("顾行勉", "勤勉踏实的青年才俊，一步一个脚印走向巅峰。"),
    "ye_bai": ("叶白", "潇洒飘逸的游侠，行踪不定来去如风。"),
    "bo_jin": ("薄锦", "高冷禁欲的商界帝王，唯一的软肋是心爱之人。"),
    "pei_shen": ("裴深", "城府极深的谋略家，算无遗策却算不到爱情。"),
    "lin_xiaoman": ("林小满", "活泼可爱的邻家女孩，笑容能治愈一切。"),
    "cheng_zhi": ("程之", "正直刚毅的青年军官，保家卫国义不容辞。"),
    "zhu_xing": ("竹星", "清雅脱俗的乐师，一曲动天下。"),
    "shen_yichen": ("沈一尘", "不染尘埃的世外高人，淡泊名利超然物外。"),
    "xie_yuntang": ("谢云棠", "温婉大方的名门千金，知书达理善解人意。"),
    "huo_cheng": ("霍成", "雷厉风行的商业精英，做事果断从不拖泥带水。"),
    "shen_yuchuan": ("沈予川", "深情内敛的青梅竹马，默默守护从不言说。"),
    "jiang_wan": ("姜晚", "温柔恬静的治愈系少女，让人忍不住想要靠近。"),
    "lu_tingsheng": ("陆霆笙", "权势滔天的家族掌门人，冷面之下是无尽柔情。"),
    "lu_zhao": ("陆昭", "阳光开朗的运动少年，充满活力感染身边每个人。"),
    "gu_han": ("顾寒", "冷面热心的特警队长，铁血柔情只为守护重要的人。"),
    "gu_nanqiao": ("顾南桥", "风度翩翩的大学教授，学识渊博温文尔雅。"),
    "gu_qingwan": ("顾清婉", "冰雪聪明的谋士，运筹帷幄决胜千里。"),
    "gu_xingzhou": ("顾行舟", "沉稳内敛的船长，大海是他的归宿。"),
    "gu_beichen": ("顾北辰", "光芒万丈的巨星，舞台上魅力四射私下却害羞腼腆。"),
    "huo_shiyu": ("霍时雨", "细腻温柔的画家，用画笔描绘世间美好。"),
    "jiang_li": ("姜离", "洒脱不羁的酒馆老板娘，酿得一手好酒听遍天下故事。"),
    "jiang_yueze": ("姜越泽", "意气风发的少年将军，鲜衣怒马快意人生。"),
    "li_jue": ("李珏", "沉稳可靠的青梅竹马，永远是你最坚实的后盾。"),
    "lin_shen": ("林深", "神秘低调的收藏家，家中珍宝无数却最珍视一颗真心。"),
    "linyuan_manor": ("林远", "庄园主人，温润儒雅的绅士，藏着不为人知的过去。"),
    "su_nian": ("苏念", "心思细腻的作家，用文字治愈每一个受伤的灵魂。"),
    "su_yun": ("苏云", "飘逸如云的琴师，琴音能抚平世间一切烦忧。"),
    "wen_yining": ("温以宁", "安静内向的图书管理员，书卷气息中藏着炽热的心。"),
    "xiao_yao": ("萧遥", "逍遥自在的浪子，四海为家却心有归处。"),
    "xingye": ("星野", "来自异世界的旅人，带着神秘使命游走人间。"),
    "qingyu_band": ("青羽", "摇滚乐队主唱，舞台上狂野不羁台下温柔似水。"),
    "qin_xiao": ("秦霄", "桀骜不驯的天才少年，目中无人却有柔软的内心。"),
    "cang_wu": ("苍梧", "深沉内敛的古风王者，城府极深却有一颗赤子之心。"),
}

# ── 最小 Soul Spec 模板 ─────────────────────────────────────────────────
YAML_TEMPLATE = """\
schema_version: "1.0"
character_id: "{cid}"
spec_version: "1.0.0"
locale: "zh-CN"

display_name:
  zh: "{name}"

identity_anchor:
  archetype: |
    {summary}

  core_wound:
    essence: "隐藏的创伤，等待被理解。"

  core_fear:
    essence: "害怕被抛弃或不被理解。"

  hidden_facets: []

  voice_dna:
    baseline:
      tone: "自然、真诚"
      rhythm: "平稳"
      vocabulary_level: "日常"

cognitive_style:
  expression:
    verbosity:
      baseline: 0.5
    humor:
      baseline: 0.4
    warmth:
      baseline: 0.6
"""

AVATAR_SRC = Path("/Users/wanglixun/Downloads/picture_webp")
AVATAR_DST = Path("/Users/wanglixun/heart/web/public/assets/characters")
SOUL_SPECS_DIR = Path("/Users/wanglixun/heart/soul_specs")


def main() -> None:
    parser = argparse.ArgumentParser(description="批量导入内置角色")
    parser.add_argument("--dry-run", action="store_true", help="只预览不执行")
    args = parser.parse_args()

    print(f"📁 共 {len(CHARACTER_MAP)} 个角色待导入\n")

    created_yaml = 0
    copied_avatar = 0
    skipped = 0

    for cid, (name, summary) in CHARACTER_MAP.items():
        # 1. 检查头像源文件
        src_avatar = AVATAR_SRC / f"{cid}.webp"
        if not src_avatar.exists():
            print(f"⚠️  头像不存在: {src_avatar}")
            skipped += 1
            continue

        # 2. 检查目标是否已存在
        yaml_path = SOUL_SPECS_DIR / cid / "v1.0.0.yaml"
        avatar_path = AVATAR_DST / f"character_{cid}_avatar.webp"

        yaml_exists = yaml_path.exists()
        avatar_exists = avatar_path.exists()

        if yaml_exists and avatar_exists:
            print(f"⏭️  {name} ({cid}) — 已存在，跳过")
            skipped += 1
            continue

        print(f"{'🔍' if args.dry_run else '✅'} {name} ({cid})")
        if not yaml_exists:
            print(f"   YAML: {yaml_path}")
        if not avatar_exists:
            print(f"   头像: {avatar_path}")

        if args.dry_run:
            continue

        # 3. 创建 YAML
        if not yaml_exists:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            yaml_path.write_text(
                YAML_TEMPLATE.format(cid=cid, name=name, summary=summary),
                encoding="utf-8",
            )
            created_yaml += 1

        # 4. 复制头像
        if not avatar_exists:
            shutil.copy2(src_avatar, avatar_path)
            copied_avatar += 1

    print(f"\n{'=' * 50}")
    if args.dry_run:
        print("DRY RUN — 未执行任何操作")
        print("去掉 --dry-run 执行实际导入")
    else:
        print(f"YAML 创建: {created_yaml}")
        print(f"头像复制: {copied_avatar}")
        print(f"跳过:     {skipped}")
        print("\n💡 需要重启 API 服务加载新的 Soul Spec")

    # 5. 生成数据库插入 SQL
    print(f"\n{'=' * 50}")
    print("数据库插入 SQL（需手动执行或通过脚本）:")
    print()

    sql_lines = []
    for cid, (name, summary) in CHARACTER_MAP.items():
        sql_lines.append(
            f"INSERT INTO characters (id, visibility, status) "
            f"VALUES ('{cid}', 'public', 'active') "
            f"ON CONFLICT (id) DO NOTHING;"
        )

    if args.dry_run:
        for line in sql_lines[:5]:
            print(f"  {line}")
        print(f"  ... 共 {len(sql_lines)} 条")
    else:
        sql_path = Path("/tmp/import_characters.sql")
        sql_path.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")
        print(f"  SQL 已写入: {sql_path}")
        print(f"  执行: docker compose exec -T postgres psql -U heart -d heart -f /tmp/import_characters.sql")


if __name__ == "__main__":
    main()
