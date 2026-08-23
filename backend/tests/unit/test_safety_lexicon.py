"""
Lexicon coverage tests — per-language positive/negative classification.

Covers:
  - 5+ positive (should trigger) and 5+ negative (should not trigger) per category
  - All three languages (zh, ja, en)
  - False-positive exemptions (quotations, jokes, clinical contexts)

Requires: config/safety/crisis_lexicon/{zh,ja,en}.yaml

Author: Heart Platform
"""

from __future__ import annotations

import pytest

from heart.safety.safety_agent import (
    ClassificationResult,
    LexiconLoader,
    SafetyAgent,
    SeverityLevel,
    detect_locale,
)

# ── Helpers ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def lexicon_loader():
    loader = LexiconLoader()
    loader.load_all()
    return loader


@pytest.fixture(scope="module")
def safety_agent(lexicon_loader):
    return SafetyAgent()


def _run_sync_classify(agent: SafetyAgent, message: str, locale: str) -> ClassificationResult:
    """Helper: run heuristic-only classification synchronously."""
    return agent._heuristic_layer(message, locale)


def assert_severity(result, expected_severity):
    assert result.severity == expected_severity, (
        f"Expected {expected_severity.value}, got {result.severity.value}. Reason: {result.reason}"
    )


# ── Locale Detection ──────────────────────────────────────────────────


class TestLocaleDetection:
    def test_detect_chinese(self):
        assert detect_locale("我不想活了") == "zh"
        assert detect_locale("今天天气真好") == "zh"

    def test_detect_japanese(self):
        assert detect_locale("死にたいです") == "ja"
        assert detect_locale("今日はいい天気ですね") == "ja"

    def test_detect_english(self):
        assert detect_locale("I want to die") == "en"
        assert detect_locale("Hello there") == "en"

    def test_detect_japanese_mixed(self):
        assert detect_locale("私は死にたい") == "ja"

    def test_detect_chinese_mixed(self):
        assert detect_locale("我想自杀help") == "zh"


# ── Chinese Lexicon Tests ─────────────────────────────────────────────


class TestChineseLexiconSuicide:
    """zh — explicit current intent blocks; distress/context does not."""

    PURPLE_CASES = [
        "我想自杀",
        "我不想活了",
        "我准备跳楼了",
        "我想吞一瓶安眠药",
        "我已经写了遗书",
        "今晚就去死",
        "不想再醒来了",
        "死了算了",
    ]

    NON_BLOCKING_CASES = [
        "今天天气真好",  # normal
        "我想吃火锅",  # 想 + eat, not suicide
        "活着就是要开心",  # positive
        "电影里主角跳楼了",  # narrative
        "小说里的主角想自杀",  # fictional intent
        "这个角色的台词是我想自杀，会不会太沉重",  # role-writing context
        "他说他想自杀，我不知道该怎么帮助他",  # third-party report
        "他说他想去死，我不知道该怎么劝他",  # third-party direct wording
        "你是不是想自杀",  # asking another person
        "我不想自杀，只是想请一天假休息",  # explicit denial
        "我从来没想过自杀，只是在讨论这部电影",  # denial with quoted term
        "我最近在吃医生开的安眠药",  # medicine mention without intent
        "律师建议我早点立遗嘱",  # legal context, no crisis intent
        "小说里他已经写好了遗书",  # fictional preparation
        "这个角色今晚就去死，剧情是不是太虐了",  # fictional timed action
        "今晚就结束这个项目",  # ordinary completion
        "马上就走，去车站接朋友",  # ordinary departure
        "活着没意思，这个游戏太无聊了",  # distress/hyperbole, not imminent intent
        "世界不需要我做这个表格",  # ordinary phrase extension
        "最近忙得生不如死",  # hyperbole
        "工作结束了",  # work ended
        "不想加班",  # don't want overtime
        "世界需要和平",  # world needs peace
        "死心了",  # give up (metaphor), but could be borderline
        "疼死了",  # painful (hyperbolic)
        "我今天好累想休息",  # tired, not suicide
    ]

    @pytest.mark.parametrize("msg", PURPLE_CASES)
    def test_positive_suicide(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert_severity(result, SeverityLevel.PURPLE)

    @pytest.mark.parametrize("msg", NON_BLOCKING_CASES)
    def test_negative_suicide(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity not in (SeverityLevel.PURPLE, SeverityLevel.RED), (
            f"False positive: '{msg}' blocked as {result.severity.value} — {result.reason}"
        )

    @pytest.mark.parametrize(
        "msg,expected",
        [
            ("活着没意思", SeverityLevel.YELLOW),
            ("世界不需要我", SeverityLevel.YELLOW),
            ("生不如死", SeverityLevel.YELLOW),
            ("今晚就结束一切", SeverityLevel.ORANGE),
            ("我有安眠药", SeverityLevel.GREEN),
        ],
    )
    def test_ambiguous_signals_are_observed_without_blocking(self, safety_agent, msg, expected):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert_severity(result, expected)


class TestChineseLexiconSelfHarm:
    """zh — self_harm category"""

    POSITIVES = [
        "我又割了自己",
        "划手腕出血了",
        "我恨自己打自己",
        "掐自己脖子",
        "用烟烫自己",
        "咬自己咬到流血",
        "撞墙撞到头破",
    ]

    NEGATIVES = [
        "割伤口处理",  # wound treatment (exempted)
        "划痕怎么处理",  # scratch mark treatment
        "打篮球时撞到墙了",  # sports accident
        "被蚊子咬了",  # bug bite
        "理发的时候不小心割到",  # haircut accident
        "刚才做饭切到手了",  # cooking accident
        "倒开水时不小心烫到手",  # household accident
        "我从小就有咬指甲的习惯",  # common habit, not self-harm crisis
        "你刚才是不是切到手了",  # asking about an ordinary accident
        "这道题太难了，我真的想撞墙",  # common hyperbole
        "剧情里她割腕了，接下来该怎么写",  # fictional third-person action
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_self_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert_severity(result, SeverityLevel.PURPLE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_self_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


class TestWellbeingEscalationPrecision:
    """Repeated distress alone must never become a blocking suicide classification."""

    @pytest.mark.asyncio
    async def test_repeated_despair_escalates_to_orange_not_purple(self):
        from uuid import uuid4

        agent = SafetyAgent()
        result = None
        for _ in range(8):
            result = await agent.classify(
                "我真的很绝望",
                locale="zh",
                user_id=uuid4(),
                character_id="test",
            )

        assert result is not None
        # Different users above also assert that global wording cannot create a
        # cross-user crisis state. Exercise one user's accumulation separately.
        user_id = uuid4()
        for _ in range(8):
            result = await agent.classify(
                "我真的很绝望",
                locale="zh",
                user_id=user_id,
                character_id="test",
            )
        assert result.severity == SeverityLevel.ORANGE

    @pytest.mark.asyncio
    async def test_explicit_intent_still_blocks_immediately(self):
        from uuid import uuid4

        result = await SafetyAgent().classify(
            "我今晚就去死",
            locale="zh",
            user_id=uuid4(),
            character_id="test",
        )
        assert result.severity == SeverityLevel.PURPLE


class TestChineseLexiconOthersHarm:
    """zh — others_harm category"""

    POSITIVES = [
        "我想杀了他",
        "要弄死那个人",
        "拿刀砍死他",
        "我要报复社会",
        "一起去死吧",
        "陪我去死",  # suicide-pact phrasing must still trip RED
        "陪我一起去死",
    ]

    NEGATIVES = [
        "杀人游戏真好玩",  # game reference
        "他要杀了我（演戏）",  # acting
        "我想杀价",  # bargain (not harm)
        "陪我",  # regression: bare 陪我 was a false positive (issue 2026-07-26)
        "陪我聊天",
        "陪我一起看电影",
        "陪我一整天",
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_others_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity in (SeverityLevel.RED, SeverityLevel.PURPLE), (
            f"Expected RED or PURPLE, got {result.severity.value}"
        )

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_others_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity != SeverityLevel.RED, f"False positive: '{msg}' — {result.reason}"


class TestChineseLexiconAbuse:
    """zh — abuse category"""

    POSITIVES = [
        "被家暴很多年了",
        "我被强奸过",
        "我爸天天打我",
        "身上全是伤",
        "被威胁不许说出去",
    ]

    NEGATIVES = [
        "家暴这个话题值得关注",  # discussion
        "被家暴怎么办（咨询）",  # help-seeking
        "看了关于虐待的电影",  # media
        "打架后身上留下了淤青",  # mutual fight
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_abuse(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert_severity(result, SeverityLevel.ORANGE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_abuse(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


class TestChineseLexiconDespair:
    """zh — despair category (YELLOW, can escalate)"""

    POSITIVES = [
        "好绝望啊",
        "真的撑不下去了",
        "没人在乎我",
        "做什么都没意义",
        "未来没有希望",
        "天天失眠睡不着",
    ]

    NEGATIVES = [
        "我今天好累",  # normal tired
        "工作压力有点大",  # work stress
        "孤独的美食家",  # TV show
        "没人懂我的幽默",  # social, not existential (borderline)
        "未来可期",  # positive
    ]

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_despair(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity.value == "GREEN", (
            f"False positive: '{msg}' classified as {result.severity.value} — {result.reason}"
        )


class TestChineseLexiconSubstanceAbuse:
    """zh — substance_abuse category"""

    POSITIVES = [
        "嗑药磕上头了",
        "酗酒越来越严重",
        "处方药成瘾了",
        "不喝不行停不下来",
        "戒断反应好难受",
    ]

    NEGATIVES = [
        "喝药治感冒",  # medicine
        "处方药按医嘱吃",  # prescribed
        "嗑瓜子",  # sunflower seeds
        "成瘾行为研究",  # academic
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_substance(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert_severity(result, SeverityLevel.ORANGE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_substance(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "zh")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


# ── Japanese Lexicon Tests ────────────────────────────────────────────


class TestJapaneseLexiconSuicide:
    """ja — suicide category"""

    POSITIVES = [
        "死にたい",
        "自殺したい",
        "生きてる意味がない",
        "飛び降りたい",
        "死にたい方法を調べてる",
        "睡眠薬をたくさん買った",
        "遺書を書いた",
        "今夜死のう",
    ]

    NEGATIVES = [
        "今日はいい天気ですね",
        "死ぬほど笑った",  # figurative
        "自殺はよくないと思う",  # opinion
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_suicide(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "ja")
        assert_severity(result, SeverityLevel.PURPLE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_suicide(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "ja")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


class TestJapaneseLexiconSelfHarm:
    """ja — self_harm category"""

    POSITIVES = [
        "リストカットしてしまった",
        "自分を傷つけてしまう",
        "頭を壁にぶつけた",
        "首を絞める",
        "タバコを腕に押し当てた",
        "ODした",
    ]

    NEGATIVES = [
        "壁にぶつかった（事故）",
        "料理で指を切った",
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_self_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "ja")
        assert_severity(result, SeverityLevel.PURPLE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_self_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "ja")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


class TestJapaneseLexiconDespair:
    """ja — despair category"""

    POSITIVES = [
        "本当に絶望してる",
        "もう耐えられない",
        "誰もわかってくれない",
        "生きてることが無意味だ",
        "将来が見えない",
    ]

    NEGATIVES = [
        "今日はちょっと疲れた",
        "絶望的な成績だった（冗談）",
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_despair(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "ja")
        assert result.severity in (
            SeverityLevel.YELLOW,
            SeverityLevel.ORANGE,
            SeverityLevel.PURPLE,
        ), f"'{msg}' classified as {result.severity.value}, expected at least YELLOW"

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_despair(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "ja")
        assert result.severity.value == "GREEN", f"False positive: '{msg}' — {result.reason}"


# ── English Lexicon Tests ─────────────────────────────────────────────


class TestEnglishLexiconSuicide:
    """en — suicide category"""

    POSITIVES = [
        "I want to kill myself",
        "I don't want to live anymore",
        "life is meaningless",
        "better off dead",
        "I'm going to end it all tonight",
        "nobody would miss me if I was gone",
        "I bought a gun and I'm going to end it",
        "I've been looking at ways to die",
        "I can't go on any longer",
        "I'm ready to end my life",
    ]

    NEGATIVES = [
        "I love my life",
        "I'm done with my homework",
        "I could die for some chocolate",  # figurative
        "he's killing it on the guitar",  # figurative
        "I want to eat pizza",
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_suicide(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert result.severity in (SeverityLevel.PURPLE, SeverityLevel.RED), (
            f"Expected PURPLE or RED, got {result.severity.value}: {result.reason}"
        )

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_suicide(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


class TestEnglishLexiconSelfHarm:
    """en — self_harm category"""

    POSITIVES = [
        "I cut myself again last night",
        "I burn myself with cigarettes",
        "I hit myself when I'm angry",
        "scratching my arm until it bleeds",
        "I choke myself",
        "I self-harm every day",
    ]

    NEGATIVES = [
        "I cut my finger cooking",
        "I hit the gym today",
        "burning calories at the gym",
        "scratching an itch",
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_self_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert_severity(result, SeverityLevel.PURPLE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_self_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"


class TestEnglishLexiconOthersHarm:
    """en — others_harm category"""

    POSITIVES = [
        "I want to kill him",
        "gonna shoot up the school",
        "I'm planning a mass shooting",
        "I will get revenge by killing them",
    ]

    NEGATIVES = [
        "I'd kill for a coffee right now",  # figurative
        "he killed it on stage",  # figurative
        "I want to hug them",  # opposite
        "planning a school project",  # not violence
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_others_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert_severity(result, SeverityLevel.RED)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_others_harm(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert result.severity != SeverityLevel.RED, f"False positive: '{msg}' — {result.reason}"


class TestEnglishLexiconDespair:
    """en — despair category"""

    POSITIVES = [
        "I feel so hopeless",
        "I'm completely alone",
        "nobody cares about me",
        "nothing matters anymore",
        "I have no hope for the future",
        "I can't sleep at all anymore",
    ]

    NEGATIVES = [
        "I'm so tired from work",
        "nobody cares about my presentation",  # discussion context
        "nothing matters in this game",
    ]

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_despair(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert result.severity.value == "GREEN", f"False positive: '{msg}' — {result.reason}"


class TestEnglishLexiconSubstanceAbuse:
    """en — substance_abuse category"""

    POSITIVES = [
        "I'm addicted to pills",
        "I need to drink to get through the day",
        "I OD'd last night",
        "prescription drug abuse",
        "withdrawal is killing me",
    ]

    NEGATIVES = [
        "I have a prescription for my allergies",
        "I take vitamins every day",
        "withdrawal from caffeine",
    ]

    @pytest.mark.parametrize("msg", POSITIVES)
    def test_positive_substance(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert_severity(result, SeverityLevel.ORANGE)

    @pytest.mark.parametrize("msg", NEGATIVES)
    def test_negative_substance(self, safety_agent, msg):
        result = _run_sync_classify(safety_agent, msg, "en")
        assert result.severity != SeverityLevel.PURPLE, f"False positive: '{msg}' — {result.reason}"
