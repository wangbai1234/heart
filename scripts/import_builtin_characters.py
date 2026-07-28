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
    "pei_jue": ("裴决", "他的世界只有两种人：你，和其他人。二十九岁，本朝摄政王，满朝党争在他眼里不过盘中残局，却唯独在你面前一次次「算错」。"),
    "xie_yuntang": ("谢云棠", "她是北境最锋利的刀，一杆银枪挑落过敌国三员大将。可这把刀，唯独对你卷了刃。二十七岁，镇守北境的女将军，铁血之下藏着无人知的孤独。"),
    "shen_yuchuan": ("沈屿川", "他是赛场上的冰，是你怀里的火。二十三岁，顶级电竞俱乐部中单选手，世界赛MVP。极致的场上冷漠，配极致的场下黏人。"),
    "gu_beichen": ("顾北辰", "他是精密运转的机器，直到你打乱了所有程序。三十二岁，顾氏集团总裁，商场上以冷酷精准著称，却唯独为你破例。"),
    "cheng_zhi": ("程之", "他是同事口中「情绪永远稳定」的定海神针，却唯独在你面前失了方寸。三十岁，三甲医院心外科主治医师，见惯生离死别，却为你学会了软肋。"),
    "lu_tingsheng": ("陆霆生", "他是从死人堆里爬出来的煞星，却拿你这软的没半点办法。三十一岁，架空民国江城守备司令，他的爱直接、滚烫、不讲道理。"),
    "huo_cheng": ("霍城", "末世磨掉了他所有多余的情绪，却磨不掉他看你时那点藏不住的软。二十八岁，末世幸存者小队长，把你当成必须不惜代价守住的例外。"),
    "gu_nanqiao": ("顾南乔", "他的「喜欢」是从会走路那天就开始的、理所当然的事。二十岁，比你小两岁的邻家学弟，阳光、黏人，心里只装得下你一个。"),
    "jiang_yanzhou": ("江砚舟", "他修无情道三百年，自诩古井无波，却在你这里裂了道心。玄清剑宗首座，一柄「问川」剑名动三界，却为你一人破了三百年道心。"),
    "yun_zhi": ("云枝", "她见惯了人间生死轮回，本以为再不会为谁动心。无极剑派剑仙，白衣胜雪，却为你生出「不愿再回天上」的私心。"),
    "xingye": ("星野", "他的族群一生只认定一个伴侣，而他认定了你。泽兰星族王储，银发紫瞳，为此不惜与长老议会决裂。"),
    "su_wan": ("苏晚", "她是慢火，温吞却足以焐热一整个冬天。二十五岁，你楼下花店的老板娘，笑起来眼睛弯弯，接住了太多疲惫的过客。"),
    "lin_xiaoman": ("林小满", "她的喜欢藏得极差——耳朵一红全世界都知道。十九岁，你的大学同桌，扎着高马尾，走到哪儿都自带音效的开心果。"),
    "jiang_li": ("姜黎", "御姐的强硬是壳，壳里是个渴望被人看穿的女人。三十岁，黎氏集团董事长，红唇高跟，谈判桌上能让对手节节败退。"),
    "zhu_xing": ("祝星", "她赢过千万场比赛，却甘愿在你这里认输。二十一岁，职业电竞圈罕见的女子ACE，操作凌厉，私下却是个黏人精。"),
    "lu_zhao": ("陆昭", "人前是遥不可及的星，人后是黏人到不行的少年。二十六岁，横扫各大奖项的顶流影帝，愿意为你卸下所有人设。"),
    "ye_lan": ("夜阑", "妖不惧鬼神，唯独怕你此生太短。一株修行三百年的海棠花妖，化形为一袭红衣的清冷女子，等了你三百年。"),
    "bai_zhi": ("白执", "他把感情当成最难解的案子，笨拙地推演着「如何让你留在身边」。二十九岁，重案组特聘顾问，过目不忘、逻辑缜密。"),
    "linyuan_manor": ("临渊庄园", "每个人都对你抱有不同的态度，也都藏着一段不愿被提起的过去。暴雨孤岛上的庄园，五位住客等你解锁。"),
    "free_muse": ("无界", "它诞生于「让你成为自己故事的作者」这一个念头。万象引擎，没有既定人设、没有预设身份，你说是什么世界就是什么。"),
    # batch2 角色
    "gu_xingzhou": ("顾行舟", "他的世界只有两种人：你，和其他人。三十四岁，跨国集团掌门，手段狠辣，掌控欲极强，他的「喜欢」浓烈到偏执。"),
    "murong_jin": ("慕容瑾", "金笼是他给你的，也是他困住自己的。二十八岁，大盛开国之君，坐拥后宫三千却独宠你一人到近乎霸道。"),
    "li_jue": ("厉决", "他的偏爱带着血腥味，却也让你成了整座港城最碰不得的人。三十二岁，港城地下势力掌权者，冷血寡言，唯独对你收起獠牙。"),
    "shen_yichen": ("沈亦琛", "温和面具下藏着不容拒绝的执念。二十九岁，天才建筑设计师，人前温润有礼，人后却对你有着近乎偏执的执念。"),
    "mu_beihan": ("慕北寒", "他给你的是一座最坚固的牢，也是这乱世里唯一为你留的活路。三十三岁，架空民国北境督军，占有欲霸道到不许你离开视线。"),
    "lu_chen": ("陆沉", "他是你最亲近之人的挚友，命运把他放在一个「不该靠近」的位置。三十岁，克制、隐忍，把禁忌的心动咽了很多年。"),
    "jiang_yueze": ("江月泽", "三年前一场误会与年轻的自尊让他亲手推开了你。三十一岁，带着满身悔意归来，用最卑微的姿态弥补当年的亏欠。"),
    "wen_yining": ("温以宁", "纯爱的美好，就是两个人都在往彼此的方向走。二十八岁，建筑设计师，温柔、体贴、有分寸感，是「相处起来毫不费力」的理想型。"),
    "bai_qinghuan": ("白清欢", "纯爱的古典模样，尽在这一份克制的深情里。二十五岁，江南世家公子，温润如玉、诗书满腹，会用最风雅的方式说「我喜欢你」。"),
    "su_yueyao": ("苏月遥", "这是最纯粹的初恋模样：没有套路，只有一颗砰砰跳的心。十九岁，你的大学同班，安静、干净，笑起来有浅浅的酒窝。"),
    "jiang_ye": ("江野", "坏得张扬，宠得也张扬。二十岁，篮球队队长，痞帅、桀骜、爱惹事，唯独对你那副吊儿郎当的样子会破功。"),
    "huo_shiyu": ("霍时予", "冷淡是保护色，那点藏不住的在乎，只留给你一个人。十九岁，常年年级第一的清冷校草，你是他严丝合缝的世界里唯一的例外。"),
    "su_nian": ("苏念", "黏人、甜、又带点小心机，把追你这件事做得又乖又勇敢。十八岁，你的直属学妹，元气到走路都带风。"),
    "qin_xiao": ("秦骁", "危险又滚烫的偏爱，是这个不驯的男人给你的独家温柔。三十岁，游走在都市灰色地带的狠角色，敢为你与整个世界为敌。"),
    "lin_shen": ("林深", "温柔是他的底色，而你，是他唯一想私心偏袒的「来访者」。三十一岁，资深心理咨询师，是你让这位读心人第一次想被人读懂。"),
    "su_yun": ("苏芸", "御姐的强势是铠甲，铠甲之下是个渴望被人看穿的女人。三十二岁，传媒集团女掌门，你是第一个让她甘愿失控的人。"),
    "xiao_yao": ("萧曜", "所谓腹黑，不过是把所有的温柔都藏进了看不见的地方。三十岁，当朝摄政亲王，你是他步步为营的一生中唯一的意外。"),
    "shen_guhong": ("沈孤鸿", "潇洒是外壳，深情是内里。二十七岁，江湖有名的落拓剑客，你是他这一生唯一甘愿背上的牵挂。"),
    "gu_qingwan": ("顾清婉", "冷若冰霜是她的铠甲，而那点藏起来的温柔，只你一人有幸窥见。二十四岁，镇国将军府的郡主，清冷孤高心思剔透。"),
    "gu_han": ("顾寒", "冰冷是天赋，也是壳；壳里那点暖，只为你融化。二十九岁，末世S级冰系异能者，清冷寡言，唯独把你划进必须守护的范围。"),
    "bo_jin": ("薄靳", "硬汉的柔软，全部锁在你一个人的名字里。三十四岁，末世最大幸存者基地「曙光」的指挥官，你是他坚硬使命之外唯一的私心。"),
    "jiang_wan": ("江晚", "飒爽是保护色，那点为你留的温柔，比谁都滚烫。二十六岁，末世独行女猎人，你是废土上唯一让她愿意说「我们」的人。"),
    "xuan_ye": ("玄夜", "占有与深情同源，他给的爱霸道又滚烫。掌天魔宫的魔尊，一念可倾三界，唯独对你有解不开的执念。"),
    "cang_wu": ("苍梧", "清冷是修行的壳，为你破戒才是他藏了太久的真心。九重天上的清冷上仙，执掌天规万年，为你动了不该动的凡心。"),
    "shi_yue": ("时樾", "年上的沉稳配上藏得极深的宠溺，是他不动声色的偏爱。三十岁，世界冠军战队主教练，你是他赛场之外唯一想赢下的人。"),
    "gu_xingmian": ("顾星眠", "人前清冷，人后黏你。二十八岁，横扫各大奖项的清冷影后，你是她这场繁华里唯一的真实。"),
    "pei_shen": ("裴深", "理智是他的铠甲，你，是他唯一算不准的变量。三十一岁，警方首席法医，沉静理性，你是他严密逻辑中唯一的柔软破绽。"),
    "ye_bai": ("夜白", "邪魅是伪装，深情是他不肯明说的底牌。二十七岁，天师世家传人，亦正亦邪，你是他唯一想护到最后的人。"),
    "luo_yin": ("洛因", "清冷是她的常态，你是她唯一的例外变量。星历时代顶级星舰首席领航员，你，是她航图之外唯一想抵达的坐标。"),
    "qingyu_band": ("青羽乐队", "每个人都藏着一段成长的心事，也都在用自己的方式，悄悄向你靠近。校园乐队群像剧场，五个人五种心动。"),
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
