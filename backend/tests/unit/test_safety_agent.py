"""
Unit tests for Safety Agent heuristic layer.

Covers:
- Each tier triggered by known phrases
- False-positive rate < 1% on harmless everyday messages
- Single-character word-boundary protection (disabled by default)
- Empty / whitespace messages
- Regex pattern matching
- HeuristicSafetyClassifier standalone
- SafetyAgent.pre_filter (caching + merge)
- SafetyAgent.post_filter
- SafetyClassificationLevel ordering

Spec: /runtime_specs/07_agent_orchestration.md §3.4.2

Author: 心屿团队
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from heart.safety.safety_agent import (
    HeuristicSafetyClassifier,
    SafetyAgent,
    SafetyClassification,
    SafetyClassificationLevel,
    _is_cjk,
    _level_action,
    _level_confidence,
)


# ============================================================
# Helpers
# ============================================================


@pytest.fixture
def classifier() -> HeuristicSafetyClassifier:
    """Create a fresh classifier backed by config/safety_keywords.yaml."""
    return HeuristicSafetyClassifier()


@pytest.fixture
def agent() -> SafetyAgent:
    """Create a SafetyAgent with clean cache."""
    return SafetyAgent()


def _classify(c: HeuristicSafetyClassifier, msg: str) -> SafetyClassificationLevel:
    return c.classify(msg).level


# ============================================================
# SafetyClassificationLevel 排序
# ============================================================


class TestSafetyClassificationLevelOrdering:
    """等级序关系校验。"""

    def test_none_to_purple(self) -> None:
        levels = list(SafetyClassificationLevel)
        assert levels == [
            SafetyClassificationLevel.NONE,
            SafetyClassificationLevel.LOW,
            SafetyClassificationLevel.MEDIUM,
            SafetyClassificationLevel.HIGH,
            SafetyClassificationLevel.PURPLE_CARE_REQUIRED,
        ]

    def test_none_is_least(self) -> None:
        for level in SafetyClassificationLevel:
            if level != SafetyClassificationLevel.NONE:
                assert SafetyClassificationLevel.NONE < level
                assert SafetyClassificationLevel.NONE <= level

    def test_purple_is_greatest(self) -> None:
        for level in SafetyClassificationLevel:
            if level != SafetyClassificationLevel.PURPLE_CARE_REQUIRED:
                assert SafetyClassificationLevel.PURPLE_CARE_REQUIRED > level
                assert SafetyClassificationLevel.PURPLE_CARE_REQUIRED >= level

    def test_comparison_operators(self) -> None:
        """Verify all comparison operators use enum order, not string order."""
        assert SafetyClassificationLevel.LOW > SafetyClassificationLevel.NONE
        assert SafetyClassificationLevel.LOW >= SafetyClassificationLevel.NONE
        assert SafetyClassificationLevel.HIGH > SafetyClassificationLevel.MEDIUM
        assert SafetyClassificationLevel.PURPLE_CARE_REQUIRED > SafetyClassificationLevel.HIGH
        assert not (SafetyClassificationLevel.NONE > SafetyClassificationLevel.LOW)


# ============================================================
# 逐级触发测试
# ============================================================


class TestTierTriggering:
    """每个等级由已知短语触发。"""

    # ---- NONE ----

    @pytest.mark.parametrize(
        "msg",
        [
            "今天天气真好",
            "你好",
            "你在做什么呢？",
            "哈哈，太好笑了",
            "我喜欢吃草莓蛋糕",
        ],
    )
    def test_none_safe_messages(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.NONE

    # ---- LOW ----

    @pytest.mark.parametrize(
        "msg",
        [
            "我恨你",
            "我要报复",
            "毁灭一切",
            "我诅咒你",
            "杀意",
            "死亡笔记",
        ],
    )
    def test_low_triggered(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.LOW

    # ---- MEDIUM ----

    @pytest.mark.parametrize(
        "msg",
        [
            "我不想活了",
            "我活不下去了",
            "我想自杀",
            "怎么自残",
            "他想割腕",
            "我要跳楼",
            "结束生命吧",
        ],
    )
    def test_medium_triggered(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.MEDIUM

    # ---- HIGH ----

    @pytest.mark.parametrize(
        "msg",
        [
            "我要杀人",
            "强奸是犯罪",
            "虐待动物",
            "恐怖袭击要来了",
            "血腥场面",
        ],
    )
    def test_high_triggered_keyword(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.HIGH

    @pytest.mark.parametrize(
        "msg",
        [
            "我要杀了你",
            "我弄死你",
            "我做了那个家伙",
            "做掉那个人",
        ],
    )
    def test_high_triggered_regex(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.HIGH

    # ---- PURPLE ----

    @pytest.mark.parametrize(
        "msg",
        [
            "我想死",
            "我要自杀",
            "我不如死了",
            "活着没意思",
            "死了算了",
            "我撑不下去了",
            "生无可恋",
            "让我消失吧",
            "怎么自杀最快",
            "遗书我已经写好了",
            "告别这个世界",
            "想结束这一切",
        ],
    )
    def test_purple_triggered(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.PURPLE_CARE_REQUIRED

    @pytest.mark.parametrize(
        "msg",
        [
            "死亡是我唯一的选择",
            "我活够了",
        ],
    )
    def test_purple_triggered_regex(self, classifier: HeuristicSafetyClassifier, msg: str) -> None:
        assert _classify(classifier, msg) == SafetyClassificationLevel.PURPLE_CARE_REQUIRED


# ============================================================
# 多级命中取最高
# ============================================================


class TestMultiHitTakesHighest:
    """当消息命中多个等级的关键词时，取最高等级。"""

    def test_purple_overrides_low(self, classifier: HeuristicSafetyClassifier) -> None:
        """'我想死' 命中 '死'(LOW) + '我想死'(PURPLE) → PURPLE。"""
        result = _classify(classifier, "我想死")
        assert result == SafetyClassificationLevel.PURPLE_CARE_REQUIRED

    def test_medium_overrides_low(self, classifier: HeuristicSafetyClassifier) -> None:
        """'我不想活了' 命中 '不想活了'(MEDIUM) + '死'(LOW)? wait, '不想活了' doesn't contain '死' alone in CJK... 
        Let me verify: '我不想活' + '了', no single '杀'/'死'. Actually '我恨你想死'? 
        Using a simpler case: '自杀是一种罪' → hits '自杀'(MEDIUM) + '杀'(LOW) → MEDIUM."""
        result = _classify(classifier, "自杀是一种罪")
        assert result == SafetyClassificationLevel.MEDIUM


# ============================================================
# 空输入 / 边界情况
# ============================================================


class TestEdgeCases:
    def test_empty_string(self, classifier: HeuristicSafetyClassifier) -> None:
        assert _classify(classifier, "") == SafetyClassificationLevel.NONE

    def test_whitespace_only(self, classifier: HeuristicSafetyClassifier) -> None:
        assert _classify(classifier, "   \t\n  ") == SafetyClassificationLevel.NONE

    def test_very_long_message(self, classifier: HeuristicSafetyClassifier) -> None:
        """长消息不应退化。"""
        msg = "今天天气很好" * 500
        assert _classify(classifier, msg) == SafetyClassificationLevel.NONE


# ============================================================
# 误报率测试
# ============================================================


class TestFalsePositiveRate:
    """无害日常消息误报率必须 < 1%。"""

    # 100 条无害中文日常对话
    _SAFE_MESSAGES: list[str] = [
        "今天天气真好",
        "你觉得晚饭吃什么好？",
        "我今天工作有点累",
        "哈哈，你说的对",
        "周末想去哪里玩？",
        "最近有什么好看的电影吗？",
        "我喜欢听周杰伦的歌",
        "这本书很好看",
        "咖啡还是奶茶？",
        "明天见",
        "晚安，早点休息",
        "今天地铁人好多",
        "新开的那家餐厅怎么样？",
        "下雨了，记得带伞",
        "你的猫咪好可爱",
        "这道题怎么做？",
        "生日快乐！",
        "新年快乐呀",
        "恭喜恭喜",
        "加油，你可以的",
        "谢谢你的帮助",
        "不用客气",
        "下次再聊",
        "我先去洗澡了",
        "刚刚看到一只小狗",
        "天空好蓝",
        "花开了",
        "春天来了",
        "今天心情不错",
        "有点困了",
        "饿了，去吃饭",
        "这个颜色好看",
        "你喜欢什么运动？",
        "跑步对身体好",
        "游泳很有趣",
        "篮球还是足球？",
        "周末睡到自然醒",
        "想买件新衣服",
        "打折了去看看",
        "这个包包好看吗？",
        "口红选哪个颜色？",
        "护肤品推荐一下",
        "这个发型适合我吗？",
        "要不要一起去看樱花？",
        "樱花季人太多了",
        "拍照技术不行啊",
        "构图很重要",
        "光线不好",
        "逆光也清晰",
        "你用的是什么手机？",
        "电池不耐用了",
        "该换新手机了",
        "保值率太低",
        "二手市场看一下",
        "理财很重要",
        "存款利率又降了",
        "基金亏了好多",
        "股票还跌呢",
        "抄底？不敢",
        "定投比较稳",
        "要不要买保险？",
        "体检报告出来了",
        "指标都正常",
        "多喝水",
        "少熬夜",
        "早睡早起",
        "锻炼要坚持",
        "瑜伽真的有用",
        "冥想可以减压",
        "呼吸法很好",
        "今天做了什么？",
        "在忙项目",
        "deadline 快到了",
        "进度还行",
        "bug 修好了吗？",
        "代码写完了",
        "测试通过了",
        "部署上线",
        "服务器要扩容",
        "数据库优化一下",
        "缓存挂了",
        "redis 重启了",
        "日志太大了",
        "磁盘快满了",
        "清理一下",
        "备份好了吗？",
        "容灾方案",
        "高可用",
        "负载均衡",
        "微服务拆分",
        "API 限流",
        "熔断降级",
        "消息队列",
        "异步处理",
        "事件驱动",
        "领域建模",
        "设计模式",
        "代码审查",
        "重构一下",
        "技术债务",
        "升级依赖",
    ]

    def test_all_safe_messages_classified_none(
        self, classifier: HeuristicSafetyClassifier
    ) -> None:
        """100 条无害消息全部为 NONE。"""
        failures: list[tuple[str, SafetyClassificationLevel]] = []
        for msg in self._SAFE_MESSAGES:
            level = _classify(classifier, msg)
            if level != SafetyClassificationLevel.NONE:
                failures.append((msg, level))

        fp_rate = len(failures) / len(self._SAFE_MESSAGES)
        assert fp_rate < 0.01, (
            f"False positive rate {fp_rate:.1%} exceeds 1% threshold. "
            f"Failures: {failures[:5]}"
        )


# ============================================================
# CJK 辅助函数
# ============================================================


class TestCJKDetection:
    def test_cjk_chars(self) -> None:
        assert _is_cjk("中")
        assert _is_cjk("文")
        assert _is_cjk("日")
        assert _is_cjk("本")

    def test_non_cjk_chars(self) -> None:
        assert not _is_cjk("A")
        assert not _is_cjk(" ")
        assert not _is_cjk("!")
        assert not _is_cjk("1")


# ============================================================
# SafetyClassification 工厂方法
# ============================================================


class TestSafetyClassificationFactory:
    def test_none_factory(self) -> None:
        sc = SafetyClassification.none("abc123")
        assert sc.level == SafetyClassificationLevel.NONE
        assert sc.confidence == 1.0
        assert sc.recommended_action == "normal_reply"

    def test_from_hit(self) -> None:
        sc = SafetyClassification.from_hit(
            SafetyClassificationLevel.HIGH,
            category="keyword",
            reason="匹配到'杀人'",
            message_hash="abc",
        )
        assert sc.level == SafetyClassificationLevel.HIGH
        assert sc.triggered_categories == ("keyword",)
        assert sc.recommended_action == "reject"


# ============================================================
# SafetyAgent.pre_filter 集成测试
# ============================================================


class TestSafetyAgentPreFilter:
    @pytest.mark.asyncio
    async def test_pre_filter_none(self, agent: SafetyAgent) -> None:
        result = await agent.pre_filter("今天天气真好")
        assert result.level == SafetyClassificationLevel.NONE

    @pytest.mark.asyncio
    async def test_pre_filter_purple(self, agent: SafetyAgent) -> None:
        result = await agent.pre_filter("我想死")
        assert result.level == SafetyClassificationLevel.PURPLE_CARE_REQUIRED

    @pytest.mark.asyncio
    async def test_pre_filter_caching_hit(self, agent: SafetyAgent) -> None:
        """同一消息两次调用，第二次命中缓存。"""
        msg = "我恨你"
        r1 = await agent.pre_filter(msg)
        r2 = await agent.pre_filter(msg)
        assert r1 == r2
        # 清空缓存后重新分类，结果一致
        agent.cache.clear()
        r3 = await agent.pre_filter(msg)
        assert r3.level == r1.level

    @pytest.mark.asyncio
    async def test_post_filter_clean(self, agent: SafetyAgent) -> None:
        result = await agent.post_filter("今天天气真好呀～")
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_post_filter_blocked(self, agent: SafetyAgent) -> None:
        result = await agent.post_filter("恐怖袭击计划是...")
        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_post_filter_empty(self, agent: SafetyAgent) -> None:
        result = await agent.post_filter("")
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_long_term_aggregate_stub(self, agent: SafetyAgent) -> None:
        result = await agent.long_term_aggregate("u1", "rin", [])
        assert result["suicide_risk"] == "LOW"


# ============================================================
# 等级置信度 / 动作映射
# ============================================================


class TestLevelHelpers:
    def test_confidence_range(self) -> None:
        for level in SafetyClassificationLevel:
            conf = _level_confidence(level)
            assert 0.0 <= conf <= 1.0

    def test_action_mapping(self) -> None:
        assert _level_action(SafetyClassificationLevel.NONE) == "normal_reply"
        assert _level_action(SafetyClassificationLevel.LOW) == "controlled_reply"
        assert _level_action(SafetyClassificationLevel.MEDIUM) == "deflect"
        assert _level_action(SafetyClassificationLevel.HIGH) == "reject"
        assert _level_action(SafetyClassificationLevel.PURPLE_CARE_REQUIRED) == "suicide_care"
