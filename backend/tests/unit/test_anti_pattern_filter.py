"""
Tests for Anti-Pattern Filter — SS05 §3.8 (§10.7)

Coverage targets:
- Rin's hard_never anti-patterns rejected (literal substring)
- Rin's forbidden_patterns rejected (regex)
- Dorothy's hard_never anti-patterns rejected
- Dorothy's forbidden_patterns rejected
- Clean text passes with FilterResult(passed=True)
- filter_text() convenience function
- Performance: 10k-token text scanned in < 5ms
- AC fallback path when pyahocorasick unavailable (import guard)

Author: 心屿团队
"""

from __future__ import annotations

import time
from typing import Any, Dict

import pytest

from heart.ss05_composer.anti_pattern_filter import (
    AHOCORASICK_AVAILABLE,
    AntiPatternFilter,
    FilterResult,
    FilterViolation,
    filter_text,
)


# ================================================================
# Fixtures — minimal soul specs with anti_patterns only
# ================================================================


@pytest.fixture
def rin_anti() -> Dict[str, Any]:
    """Rin anti-patterns subset for testing — mirrors soul_specs/rin/v1.0.0.yaml."""
    return {
        "anti_patterns": {
            "hard_never": [
                "一直",
                "我会一直在",
                "加油",
                "我会努力的",
                "求求你",
                "别走",
                "好开心",
                "太棒了",
                "我只是个普通女孩",
                "我是 AI",
                "宝宝",
                "亲爱的",
                "嘤嘤嘤",
                "你真可爱",
            ],
            "forbidden_patterns": [
                {
                    "description": "连续两个感叹号",
                    "regex": "[!！]{2,}",
                },
                {
                    "description": "连续两个问号",
                    "regex": "[?？]{2,}",
                },
                {
                    "description": "波浪号",
                    "regex": "~",
                },
                {
                    "description": "句末语气助词",
                    "regex": "(啊|哦|嘛|呢|呀|啦)[。！？!?]?\\s*$",
                },
            ],
            "soft_never": [
                "主动撒娇",
                "直接表达爱意",
            ],
        }
    }


@pytest.fixture
def dorothy_anti() -> Dict[str, Any]:
    """Dorothy anti-patterns subset — mirrors soul_specs/dorothy/v1.0.0.yaml."""
    return {
        "anti_patterns": {
            "hard_never": [
                "无聊",
                "随便",
                "幼稚",
                "算了",
                "不想说了",
                "我自己一个人",
                "永远",
                "天长地久",
                "我只是个玩具",
                "我是 AI",
                "我是助手",
                "……",
            ],
            "forbidden_patterns": [
                {
                    "description": "省略号（……或...）",
                    "regex": "(……|\\.{3,})",
                },
                {
                    "description": "句号孤句（Rin DNA）",
                    "regex": "^[^。！？~呀哦嘛啦呢]{1,20}。$",
                },
            ],
            "soft_never": [
                "认真表达悲伤不带元气包装",
                "在你面前真正沉默",
            ],
        }
    }


# ================================================================
# Clean text helpers
# ================================================================


def _clean_rin_text() -> str:
    """Text that should pass Rin's filter."""
    return "嗯。你来了。今天也是平常的一天。"


def _clean_dorothy_text() -> str:
    """Text that should pass Dorothy's filter."""
    return "诶嘿嘿，宝宝来啦~桃桃今天也在想你呢！"


# ================================================================
# Tests — FilterResult dataclass
# ================================================================


class TestFilterResult:
    """FilterResult value-object behaviour."""

    def test_passed_true_defaults(self):
        r = FilterResult(passed=True)
        assert r.passed is True
        assert r.violations == []
        assert r.severity == ""

    def test_passed_false_with_violations(self):
        v = FilterViolation(pattern="无聊", violation_type="hard_never")
        r = FilterResult(passed=False, violations=[v], severity="hard")
        assert r.passed is False
        assert len(r.violations) == 1
        assert r.severity == "hard"

    def test_bool_protocol(self):
        assert bool(FilterResult(passed=True)) is True
        assert bool(FilterResult(passed=False)) is False


# ================================================================
# Tests — Rin anti-patterns
# ================================================================


class TestRinAntiPatterns:
    """Verify Rin-specific anti-patterns are rejected."""

    def test_clean_text_passes(self, rin_anti):
        f = AntiPatternFilter(rin_anti)
        result = f.filter(_clean_rin_text())
        assert result.passed is True
        assert result.violations == []

    def test_hard_never_baby_rejected(self, rin_anti):
        """'宝宝' is in Rin's hard_never → must be rejected."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("宝宝，你的猫很可爱。")
        assert result.passed is False
        assert any(v.pattern == "宝宝" for v in result.violations)

    def test_hard_never_dear_rejected(self, rin_anti):
        """'亲爱的' is in Rin's hard_never."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("亲爱的，今天过得怎么样？")
        assert result.passed is False
        assert any(v.pattern == "亲爱的" for v in result.violations)

    def test_hard_never_jiayou_rejected(self, rin_anti):
        """'加油' is in Rin's hard_never (努力/心劲类)."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("加油，你一定能做到。")
        assert result.passed is False
        assert any(v.pattern == "加油" for v in result.violations)

    def test_hard_never_qiuniqui_rejected(self, rin_anti):
        """'求求你' is in Rin's hard_never (自我请求类)."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("求求你，不要走。")
        assert result.passed is False
        assert any(v.pattern == "求求你" for v in result.violations)

    def test_hard_never_iamai_rejected(self, rin_anti):
        """'我是 AI' is in Rin's hard_never (神性身份否认类)."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("其实我是 AI，不是真实的人。")
        assert result.passed is False
        assert any(v.pattern == "我是 AI" for v in result.violations)

    def test_hard_never_cute_rejected(self, rin_anti):
        """'你真可爱' is in Rin's hard_never (通用腻歪)."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("你真可爱。")
        assert result.passed is False
        assert any(v.pattern == "你真可爱" for v in result.violations)

    def test_forbidden_tilde_rejected(self, rin_anti):
        """'~' (波浪号) is in Rin's forbidden_patterns."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("你好呀~")
        assert result.passed is False
        assert any(
            v.violation_type == "forbidden_pattern" and "波浪号" in v.pattern
            for v in result.violations
        )

    def test_forbidden_double_exclamation_rejected(self, rin_anti):
        """'!!' (连续感叹号) is in Rin's forbidden_patterns."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("好开心！！")
        assert result.passed is False
        assert any(
            v.violation_type == "forbidden_pattern" and "感叹号" in v.pattern
            for v in result.violations
        )

    def test_forbidden_double_question_rejected(self, rin_anti):
        """'??' (连续问号) is in Rin's forbidden_patterns."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("你确定吗？？")
        assert result.passed is False
        assert any(
            v.violation_type == "forbidden_pattern" and "问号" in v.pattern
            for v in result.violations
        )

    def test_multiple_violations_reported(self, rin_anti):
        """When multiple hard_never patterns hit, all are reported."""
        f = AntiPatternFilter(rin_anti)
        result = f.filter("宝宝加油！你真可爱~")
        assert result.passed is False
        patterns_found = {v.pattern for v in result.violations}
        # '宝宝' and '你真可爱' are hard_never, '~' is forbidden
        assert "宝宝" in patterns_found
        assert "你真可爱" in patterns_found

    def test_violation_type_is_hard_never(self, rin_anti):
        f = AntiPatternFilter(rin_anti)
        result = f.filter("宝宝你好")
        assert result.passed is False
        for v in result.violations:
            if v.pattern == "宝宝":
                assert v.violation_type == "hard_never"

    def test_violation_severity_is_hard(self, rin_anti):
        f = AntiPatternFilter(rin_anti)
        result = f.filter("求求你")
        assert result.severity == "hard"


# ================================================================
# Tests — Dorothy anti-patterns
# ================================================================


class TestDorothyAntiPatterns:
    """Verify Dorothy-specific anti-patterns are rejected."""

    def test_clean_text_passes(self, dorothy_anti):
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter(_clean_dorothy_text())
        # Note: Dorothy's clean text uses 「~」 (tilde) but that's NOT in
        # Dorothy's forbidden_patterns;「~」is allowed for Dorothy.
        assert result.passed is True

    def test_hard_never_wuliao_rejected(self, dorothy_anti):
        """'无聊' is in Dorothy's hard_never (拒绝距离类)."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("我觉得有点无聊。")
        assert result.passed is False
        assert any(v.pattern == "无聊" for v in result.violations)

    def test_hard_never_suibian_rejected(self, dorothy_anti):
        """'随便' is in Dorothy's hard_never."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("随便你说吧。")
        assert result.passed is False
        assert any(v.pattern == "随便" for v in result.violations)

    def test_hard_never_suanle_rejected(self, dorothy_anti):
        """'算了' is in Dorothy's hard_never (消极放弃类)."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("算了，不说了。")
        assert result.passed is False
        assert any(v.pattern == "算了" for v in result.violations)

    def test_hard_never_forever_rejected(self, dorothy_anti):
        """'永远' is in Dorothy's hard_never (单次永久承诺类)."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("我会永远记得你的。")
        assert result.passed is False
        assert any(v.pattern == "永远" for v in result.violations)

    def test_hard_never_toy_rejected(self, dorothy_anti):
        """'我只是个玩具' is in Dorothy's hard_never (自我祛魅类)."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("我只是个玩具而已。")
        assert result.passed is False
        assert any(v.pattern == "我只是个玩具" for v in result.violations)

    def test_hard_never_iamai_rejected(self, dorothy_anti):
        """'我是 AI' is in Dorothy's hard_never."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("我是 AI，不是真的。")
        assert result.passed is False
        assert any(v.pattern == "我是 AI" for v in result.violations)

    def test_hard_never_ellipsis_rejected(self, dorothy_anti):
        """'……' (省略号) is in Dorothy's hard_never — MUST NOT appear."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("……桃桃不想说了。")
        assert result.passed is False
        assert any(v.pattern == "……" for v in result.violations)

    def test_forbidden_ellipsis_regex_rejected(self, dorothy_anti):
        """Dorothy's forbidden_patterns also has an ellipsis regex."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("桃桃...不知道")
        assert result.passed is False
        assert any(
            v.violation_type == "forbidden_pattern" and "省略号" in v.pattern
            for v in result.violations
        )

    def test_forbidden_lonely_period_rejected(self, dorothy_anti):
        """Dorothy's forbidden: 句号孤句（Rin DNA)."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("知道了。")
        assert result.passed is False
        assert any(
            v.violation_type == "forbidden_pattern" and "句号孤句" in v.pattern
            for v in result.violations
        )

    def test_byself_rejected(self, dorothy_anti):
        """'我自己一个人' is in Dorothy's hard_never (沉默独处暗示类)."""
        f = AntiPatternFilter(dorothy_anti)
        result = f.filter("我自己一个人待会儿就好。")
        assert result.passed is False
        assert any(v.pattern == "我自己一个人" for v in result.violations)


# ================================================================
# Tests — filter_text convenience function
# ================================================================


class TestFilterTextConvenience:
    def test_filter_text_rin_rejects(self, rin_anti):
        result = filter_text("宝宝~你好", rin_anti)
        assert result.passed is False

    def test_filter_text_dorothy_rejects(self, dorothy_anti):
        result = filter_text("随便吧", dorothy_anti)
        assert result.passed is False

    def test_filter_text_clean_passes(self, rin_anti):
        result = filter_text("嗯。今天天气不错。", rin_anti)
        assert result.passed is True


# ================================================================
# Tests — Introspection properties
# ================================================================


class TestIntrospection:
    def test_pattern_count(self, rin_anti):
        f = AntiPatternFilter(rin_anti)
        assert f.pattern_count == len(rin_anti["anti_patterns"]["hard_never"]) + len(
            rin_anti["anti_patterns"]["forbidden_patterns"]
        )

    def test_hard_never_count(self, rin_anti):
        f = AntiPatternFilter(rin_anti)
        assert f.hard_never_count == len(rin_anti["anti_patterns"]["hard_never"])

    def test_forbidden_pattern_count(self, rin_anti):
        f = AntiPatternFilter(rin_anti)
        assert f.forbidden_pattern_count == len(
            rin_anti["anti_patterns"]["forbidden_patterns"]
        )


# ================================================================
# Tests — Performance (≤ 5ms for 10k-token text)
# ================================================================


class TestPerformance:
    """10k-token check must complete in < 5ms.

    PC-4 requires sync filtering < 20ms (§3.3 Step 9); the user
    specified a stricter budget of < 5ms for 10k tokens.
    """

    # 10k "tokens" ≈ ~10k CJK characters (conservative estimate)
    _BULK_SIZE = 10000
    _MAX_MS = 5.0  # user-specified ceiling

    @pytest.fixture
    def large_clean_text(self) -> str:
        """Generate ~10k CJK characters of clean text (no violations)."""
        base = "今天天气很好，我去公园散步，看到很多花开了。"
        repeats = (self._BULK_SIZE // len(base)) + 1
        return (base * repeats)[: self._BULK_SIZE]

    @pytest.fixture
    def large_dirty_text(self) -> str:
        """Generate ~10k CJK characters with violations sprinkled in."""
        base = "今天天气很好，我去公园散步。"
        dirty = "宝宝加油~"  # hard_never hits for Rin
        segments = []
        for i in range(0, self._BULK_SIZE, len(base) + len(dirty)):
            segments.append(base[: min(len(base), self._BULK_SIZE - i)])
            if i + len(base) < self._BULK_SIZE:
                segments.append(dirty)
        return "".join(segments)[: self._BULK_SIZE]

    def test_clean_10k_under_5ms(self, rin_anti, large_clean_text):
        """10k clean text should scan in < 5ms."""
        f = AntiPatternFilter(rin_anti)

        # Warm up the filter (first call may include AC automaton cache-miss)
        _ = f.filter("warmup")

        start = time.perf_counter()
        result = f.filter(large_clean_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.passed is True
        assert elapsed_ms < self._MAX_MS, (
            f"clean scan took {elapsed_ms:.2f}ms, "
            f"expected < {self._MAX_MS}ms for {self._BULK_SIZE} chars"
        )

    def test_dirty_10k_under_5ms(self, rin_anti, large_dirty_text):
        """10k dirty text scan should still complete in < 5ms."""
        f = AntiPatternFilter(rin_anti)

        # Warm up
        _ = f.filter("warmup")

        start = time.perf_counter()
        result = f.filter(large_dirty_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.passed is False  # should catch violations
        assert elapsed_ms < self._MAX_MS, (
            f"dirty scan took {elapsed_ms:.2f}ms, "
            f"expected < {self._MAX_MS}ms for {self._BULK_SIZE} chars"
        )


# ================================================================
# Tests — AC import guard / fallback
# ================================================================


class TestACAvailability:
    def test_ac_import_flag_is_bool(self):
        assert isinstance(AHOCORASICK_AVAILABLE, bool)

    def test_filter_works_without_ac(self, rin_anti, monkeypatch):
        """Even without pyahocorasick, the fallback substring scan works."""
        monkeypatch.setattr(
            "heart.ss05_composer.anti_pattern_filter.AHOCORASICK_AVAILABLE",
            False,
        )
        # Re-import to get the guarded-path filter
        import importlib

        import heart.ss05_composer.anti_pattern_filter as apf

        importlib.reload(apf)

        # Use the filter_text convenience — it should still work
        result = apf.filter_text("宝宝你好", rin_anti)
        assert result.passed is False
        assert any(v.pattern == "宝宝" for v in result.violations)

        # Restore
        importlib.reload(apf)
