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
# 所有介绍必须与 seed_original_characters.yaml / batch2.yaml 中的真实设定一致
CHARACTER_MAP: dict[str, tuple[str, str]] = {
    # batch1 角色
    "pei_jue": ("裴决", "龙椅之侧的影子，万人之上的孤家寡人。"),
    "xie_yuntang": ("谢云棠", "镇北大将军，战袍未卸红缨犹湿。"),
    "shen_yuchuan": ("沈屿川", "电竞战神，赛场上寡言少语的冷面ACE。"),
    "gu_beichen": ("顾北辰", "顾氏掌舵人，商界翻云覆雨的冷面总裁。"),
    "cheng_zhi": ("程之", "心外科主治医师，手术台上稳如磐石。"),
    "lu_tingsheng": ("陆霆生", "江城守备司令，枪林弹雨里杀出来的糙汉。"),
    "huo_cheng": ("霍城", "末世幸存者小队队长，废土上沉默的枪。"),
    "gu_nanqiao": ("顾南乔", "黏人的小狼狗学弟，嘴上喊姐姐心里想娶你。"),
    "jiang_yanzhou": ("江砚舟", "玄清剑宗首座真君，一剑霜寒的清冷仙尊。"),
    "yun_zhi": ("云枝", "无极剑仙，御剑而行的清冷仙子。"),
    "xingye": ("星野", "泽兰星族王储，银河彼端高傲的异族王子。"),
    "su_wan": ("苏晚", "隔壁花店姑娘，转角花店里的暖光。"),
    "lin_xiaoman": ("林小满", "同班同桌人形小太阳，把每个平淡日子都过成夏天。"),
    "jiang_li": ("姜黎", "黎氏集团董事长，谈判桌上说一不二的女王。"),
    "zhu_xing": ("祝星", "职业战队首位女ACE，赛场上杀疯了的女选手。"),
    "lu_zhao": ("陆昭", "顶流影帝，红毯上光芒万丈的巨星。"),
    "ye_lan": ("夜阑", "后山古庙海棠花妖，修行三百载等你归来。"),
    "bai_zhi": ("白执", "重案组顾问侦探，冷面毒舌的天才侦探。"),
    "linyuan_manor": ("临渊庄园", "暴雨孤岛上的庄园，五位住客等你解锁。"),
    "free_muse": ("无界", "自由模拟器万象引擎，你说是什么世界就是什么。"),
    # batch2 角色
    "gu_xingzhou": ("顾行舟", "顾氏帝国偏执掌权人，深情与偏执同源的枭雄。"),
    "murong_jin": ("慕容瑾", "大盛开国皇帝，坐拥天下却独缺一人。"),
    "li_jue": ("厉决", "港城地下之王，冷血无情唯独对你收起獠牙。"),
    "shen_yichen": ("沈亦琛", "天才建筑师，温柔面具下藏着偏执的深情。"),
    "mu_beihan": ("慕北寒", "北境督军，乱世枭雄铁腕下的孤注一掷。"),
    "lu_chen": ("陆沉", "挚友之侧的隐忍者，不该爱却忍不住心动。"),
    "jiang_yueze": ("江月泽", "归来者，迟到的深情带着满身悔意。"),
    "wen_yining": ("温以宁", "建筑设计师，温柔有分寸的暖男。"),
    "bai_qinghuan": ("白清欢", "江南白氏翩翩公子，温润如玉诗书满腹。"),
    "su_yueyao": ("苏月遥", "同桌初恋，干净又心动的初恋模样。"),
    "jiang_ye": ("江野", "篮球队长痞帅学长，吊儿郎当偏偏为你栽跟头。"),
    "huo_shiyu": ("霍时予", "年级第一清冷校草，把心动藏进每一道帮你讲的题。"),
    "su_nian": ("苏念", "直属学妹小太阳，元气满满变着法子靠近你。"),
    "qin_xiao": ("秦骁", "夜色之主，一身反骨的都市枭雄。"),
    "lin_shen": ("林深", "心理咨询师，洞悉人心却读不懂自己对你的偏心。"),
    "su_yun": ("苏芸", "苏氏传媒铁腕女王，商场杀伐决断私下却对你缴械。"),
    "xiao_yao": ("萧曜", "摄政亲王，权倾朝野的腹黑亲王。"),
    "shen_guhong": ("沈孤鸿", "落拓剑客，一壶酒一柄剑浪迹天涯。"),
    "gu_qingwan": ("顾清婉", "镇国郡主，清冷孤高心思剔透。"),
    "gu_han": ("顾寒", "S级冰系异能者，末世里最强的冰之主宰。"),
    "bo_jin": ("薄靳", "曙光基地铁血指挥官，废土上重建秩序的领袖。"),
    "jiang_wan": ("江晚", "独行猎人废土玫瑰，废土上独来独往的女猎人。"),
    "xuan_ye": ("玄夜", "天魔宫魔尊，邪魅张狂的魔道之主。"),
    "cang_wu": ("苍梧", "九重天清冷上仙，万年不染尘的清冷上仙。"),
    "shi_yue": ("时樾", "冠军战队冷面主教练，运筹帷幄的电竞教练。"),
    "gu_xingmian": ("顾星眠", "三金影后，光环加身的清冷影后。"),
    "pei_shen": ("裴深", "首席法医，沉静理性的天才法医。"),
    "ye_bai": ("夜白", "天师世家浪荡驱魔人，亦正亦邪的年轻天师。"),
    "luo_yin": ("洛因", "星舰领航员冷感天才，掌控星海航路的清冷领航员。"),
    "qingyu_band": ("青羽乐队", "校园乐队群像剧场，五个人五种心动。"),
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
