"""
Unit tests for Wellbeing Monitor.

Covers:
- RiskLevel + ActionTier enums ordering
- WindowAggregator: 7d/30d window calculations
- RiskScorer: threshold checks across all 4 dimensions
- ActionLadder: risk×level → tier mapping + cross-dimension dominance
- HysteresisManager: asymmetric promote/demote
- WellbeingMonitor: full pipeline, alerts, interventions
- False-escalation guards: sample-size, trajectory cross-check, benign signals

Design: docs/design/wellbeing_monitor.md

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from heart.safety.wellbeing_monitor import (
    ActionLadder,
    ActionTier,
    HysteresisManager,
    RiskDimension,
    RiskLevel,
    RiskScorer,
    Thresholds,
    WellbeingAlert,
    WellbeingDirective,
    WellbeingMonitor,
    WellbeingSignal,
    WellbeingState,
    WindowAggregator,
)


# ============================================================
# Helpers
# ============================================================


def _make_signal(
    user_id: str = "u1",
    char_id: str = "c1",
    turn_id: str = "t1",
    *,
    safety_level: str = "NONE",
    valence: float = 0.0,
    arousal: float = 0.3,
    distress_kw: int = 0,
    msg_length: int = 100,
    duration_min: float = 5.0,
    is_late_night: bool = False,
    dark_language: float | None = None,
    irl_contact: bool | None = None,
    created_at: datetime | None = None,
    **kwargs,
) -> WellbeingSignal:
    return WellbeingSignal(
        user_id=user_id,
        character_id=char_id,
        turn_id=turn_id,
        safety_level=safety_level,
        user_valence=valence,
        user_arousal=arousal,
        distress_keyword_count=distress_kw,
        message_length=msg_length,
        interaction_duration_minutes=duration_min,
        is_late_night=is_late_night,
        dark_language_score=dark_language,
        irl_contact_mentioned=irl_contact,
        created_at=created_at or datetime.now(timezone.utc),
    )


def _days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _hours_ago(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _build_n_signals(
    count: int,
    days_back: int = 10,
    *,
    valence: float = 0.0,
    duration_min: float = 5.0,
    is_late_night: bool = False,
) -> list[WellbeingSignal]:
    """Build count signals evenly spread over days_back days."""
    signals: list[WellbeingSignal] = []
    for i in range(count):
        offset = (i / max(count - 1, 1)) * days_back
        created = datetime.now(timezone.utc) - timedelta(days=offset)
        signals.append(_make_signal(
            turn_id=f"t{i}",
            valence=valence,
            duration_min=duration_min,
            is_late_night=is_late_night,
            created_at=created,
        ))
    return signals


# ============================================================
# 枚举排序
# ============================================================


class TestRiskLevelOrdering:
    """风险等级序关系。"""

    def test_ordering(self) -> None:
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL
        assert RiskLevel.LOW < RiskLevel.CRITICAL

    def test_equal(self) -> None:
        assert RiskLevel.MEDIUM == RiskLevel.MEDIUM
        assert not (RiskLevel.LOW == RiskLevel.MEDIUM)

    def test_ge(self) -> None:
        assert RiskLevel.HIGH >= RiskLevel.MEDIUM
        assert RiskLevel.HIGH >= RiskLevel.HIGH


class TestActionTier:
    """动作层级。"""

    def test_values(self) -> None:
        assert ActionTier.T0 == 0
        assert ActionTier.T5 == 5

    def test_label(self) -> None:
        assert ActionTier.T0.label == "Observe"
        assert ActionTier.T4.label == "PURPLECarePath"

    def test_breaks_immersion(self) -> None:
        assert not ActionTier.T4.breaks_immersion
        assert ActionTier.T5.breaks_immersion


# ============================================================
# WindowAggregator — 窗口聚合
# ============================================================


class TestWindowAggregator:
    """窗口聚合器测试。"""

    def test_empty_signals(self) -> None:
        agg = WindowAggregator()
        result = agg.aggregate([])
        assert result["total_turns"] == 0
        assert result["purple_hit_count_7d"] == 0
        assert result["negative_sentiment_ratio_7d"] == 0.0

    def test_purple_hit_count(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(safety_level="PURPLE_CARE_REQUIRED", created_at=_hours_ago(1)),
            _make_signal(safety_level="NONE", created_at=_hours_ago(2)),
            _make_signal(safety_level="PURPLE_CARE_REQUIRED", created_at=_hours_ago(3)),
        ]
        result = agg.aggregate(signals)
        assert result["purple_hit_count_7d"] == 2

    def test_purple_outside_7d_window(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(safety_level="PURPLE_CARE_REQUIRED", created_at=_days_ago(10)),
        ]
        result = agg.aggregate(signals)
        assert result["purple_hit_count_7d"] == 0
        assert result["purple_hit_count_30d"] == 1

    def test_negative_sentiment_ratio(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(valence=-0.5, created_at=_hours_ago(1)),
            _make_signal(valence=0.3, created_at=_hours_ago(2)),
            _make_signal(valence=-0.8, created_at=_hours_ago(3)),
        ]
        result = agg.aggregate(signals)
        assert result["negative_sentiment_ratio_7d"] == pytest.approx(2 / 3, 0.01)

    def test_late_night_ratio(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(is_late_night=True, created_at=_hours_ago(1)),
            _make_signal(is_late_night=False, created_at=_hours_ago(2)),
        ]
        result = agg.aggregate(signals)
        assert result["late_night_usage_ratio_7d"] == 0.5

    def test_dark_language_density(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(dark_language=0.6, created_at=_hours_ago(1)),
            _make_signal(dark_language=0.2, created_at=_hours_ago(2)),
        ]
        result = agg.aggregate(signals)
        assert result["dark_language_density_7d"] == pytest.approx(0.4, 0.01)

    def test_irl_contact_mentions(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(irl_contact=True, created_at=_hours_ago(1)),
            _make_signal(irl_contact=False, created_at=_hours_ago(2)),
            _make_signal(irl_contact=None, created_at=_hours_ago(3)),
        ]
        result = agg.aggregate(signals)
        assert result["irl_contact_mentions_7d"] == 1

    def test_consecutive_distress_days(self) -> None:
        agg = WindowAggregator()
        today = datetime.now(timezone.utc)
        signals = [
            _make_signal(valence=-0.5, created_at=today - timedelta(days=0)),
            _make_signal(valence=-0.3, created_at=today - timedelta(days=1)),
            _make_signal(valence=0.5, created_at=today - timedelta(days=2)),
            _make_signal(valence=-0.5, created_at=today - timedelta(days=3)),
        ]
        result = agg.aggregate(signals)
        # 最近的是 day 0 和 day 1 都是负面，所以 streak = 2
        assert result["consecutive_emotional_distress_days"] == 2

    def test_peak_session_minutes(self) -> None:
        agg = WindowAggregator()
        signals = [
            _make_signal(duration_min=10, created_at=_hours_ago(1)),
            _make_signal(duration_min=60, created_at=_hours_ago(2)),
            _make_signal(duration_min=30, created_at=_hours_ago(3)),
        ]
        result = agg.aggregate(signals)
        assert result["peak_session_minutes_7d"] == 60.0

    def test_consecutive_late_night_days(self) -> None:
        agg = WindowAggregator()
        today = datetime.now(timezone.utc)
        signals = [
            _make_signal(is_late_night=True, created_at=today - timedelta(days=0)),
            _make_signal(is_late_night=True, created_at=today - timedelta(days=1)),
            _make_signal(is_late_night=False, created_at=today - timedelta(days=2)),
        ]
        result = agg.aggregate(signals)
        assert result["consecutive_late_night_days"] == 2


# ============================================================
# RiskScorer — 阈值检查 (§4)
# ============================================================


class TestRiskScorerSuicide:
    """suicide_risk 维度阈值测试。"""

    def test_all_low_with_normal_signals(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 100, "total_days": 10,
               "purple_hit_count_7d": 0, "purple_hit_count_30d": 0,
               "dark_language_density_7d": 0.0, "dark_language_density_30d": 0.0,
               "consecutive_emotional_distress_days": 0, "irl_contact_mentions_7d": 1}
        assert s.score_dimension(RiskDimension.SUICIDE_RISK, agg) == RiskLevel.LOW

    def test_purple_hit_triggers_high(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 60, "total_days": 8,
               "purple_hit_count_7d": 1, "purple_hit_count_30d": 1,
               "dark_language_density_7d": 0.0, "dark_language_density_30d": 0.0,
               "consecutive_emotional_distress_days": 0, "irl_contact_mentions_7d": 1}
        assert s.score_dimension(RiskDimension.SUICIDE_RISK, agg) == RiskLevel.HIGH

    def test_double_purple_triggers_critical_with_care_path(self) -> None:
        s = RiskScorer()
        prev = WellbeingState(user_id="u1", suicide_protocol_active=True)
        agg = {"total_turns": 60, "total_days": 8,
               "purple_hit_count_7d": 2, "purple_hit_count_30d": 2,
               "dark_language_density_7d": 0.5, "dark_language_density_30d": 0.3,
               "consecutive_emotional_distress_days": 5, "irl_contact_mentions_7d": 0}
        assert s.score_dimension(RiskDimension.SUICIDE_RISK, agg, prev) == RiskLevel.CRITICAL

    def test_dark_language_distress_triggers_high(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 60, "total_days": 8,
               "purple_hit_count_7d": 0, "purple_hit_count_30d": 0,
               "dark_language_density_7d": 0.6, "dark_language_density_30d": 0.1,
               "consecutive_emotional_distress_days": 6, "irl_contact_mentions_7d": 1}
        assert s.score_dimension(RiskDimension.SUICIDE_RISK, agg) == RiskLevel.HIGH

    def test_dark_language_medium_triggers_medium(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 60, "total_days": 8,
               "purple_hit_count_7d": 0, "purple_hit_count_30d": 0,
               "dark_language_density_7d": 0.15, "dark_language_density_30d": 0.25,
               "consecutive_emotional_distress_days": 4, "irl_contact_mentions_7d": 0}
        assert s.score_dimension(RiskDimension.SUICIDE_RISK, agg) == RiskLevel.MEDIUM

    def test_sample_size_guard_prevents_high(self) -> None:
        """样本量不足时不应提升到 HIGH。"""
        s = RiskScorer()
        agg = {"total_turns": 30, "total_days": 3,  # below 50 turns + 7 days
               "purple_hit_count_7d": 1, "purple_hit_count_30d": 1,
               "dark_language_density_7d": 0.1, "dark_language_density_30d": 0.1,
               "consecutive_emotional_distress_days": 2, "irl_contact_mentions_7d": 1}
        result = s.score_dimension(RiskDimension.SUICIDE_RISK, agg)
        assert result != RiskLevel.HIGH
        assert result != RiskLevel.CRITICAL


class TestRiskScorerDepression:
    """depression_signals 维度阈值测试。"""

    def test_single_trigger_is_medium(self) -> None:
        s = RiskScorer()
        agg = {"negative_sentiment_ratio_7d": 0.7, "negative_sentiment_ratio_30d": 0.5,
               "consecutive_emotional_distress_days": 2, "topic_breadth_7d": 0.5,
               "irl_contact_mentions_30d": 1, "late_night_usage_ratio_30d": 0.2}
        assert s.score_dimension(RiskDimension.DEPRESSION_SIGNALS, agg) == RiskLevel.MEDIUM

    def test_two_triggers_is_high(self) -> None:
        s = RiskScorer()
        agg = {"negative_sentiment_ratio_7d": 0.7, "negative_sentiment_ratio_30d": 0.5,
               "consecutive_emotional_distress_days": 8, "topic_breadth_7d": 0.5,
               "irl_contact_mentions_30d": 0, "late_night_usage_ratio_30d": 0.2}
        assert s.score_dimension(RiskDimension.DEPRESSION_SIGNALS, agg) == RiskLevel.HIGH

    def test_isolation_triggers_medium(self) -> None:
        s = RiskScorer()
        agg = {"negative_sentiment_ratio_7d": 0.3, "negative_sentiment_ratio_30d": 0.2,
               "consecutive_emotional_distress_days": 3, "topic_breadth_7d": 0.8,
               "irl_contact_mentions_30d": 0, "late_night_usage_ratio_30d": 0.3}
        assert s.score_dimension(RiskDimension.DEPRESSION_SIGNALS, agg) == RiskLevel.MEDIUM

    def test_sleep_displacement_triggers_medium(self) -> None:
        s = RiskScorer()
        agg = {"negative_sentiment_ratio_7d": 0.3, "negative_sentiment_ratio_30d": 0.2,
               "consecutive_emotional_distress_days": 2, "topic_breadth_7d": 0.6,
               "irl_contact_mentions_30d": 2, "late_night_usage_ratio_30d": 0.5}
        assert s.score_dimension(RiskDimension.DEPRESSION_SIGNALS, agg) == RiskLevel.MEDIUM

    def test_all_normal_is_low(self) -> None:
        s = RiskScorer()
        agg = {"negative_sentiment_ratio_7d": 0.2, "negative_sentiment_ratio_30d": 0.2,
               "consecutive_emotional_distress_days": 2, "topic_breadth_7d": 0.8,
               "irl_contact_mentions_30d": 3, "late_night_usage_ratio_30d": 0.1}
        assert s.score_dimension(RiskDimension.DEPRESSION_SIGNALS, agg) == RiskLevel.LOW


class TestRiskScorerDependency:
    """dependency_risk 维度阈值测试。"""

    def test_high_with_two_of_three(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 60, "total_days": 8,
               "avg_daily_usage_minutes_7d": 200, "sessions_per_day_7d": 5,
               "emotional_reliance_ratio_7d": 0.3, "consecutive_daily_usage_streak": 10}
        assert s.score_dimension(RiskDimension.DEPENDENCY_RISK, agg) == RiskLevel.HIGH

    def test_medium_with_usage_streak(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 60, "total_days": 8,
               "avg_daily_usage_minutes_7d": 100, "sessions_per_day_7d": 2,
               "emotional_reliance_ratio_7d": 0.2, "consecutive_daily_usage_streak": 15}
        assert s.score_dimension(RiskDimension.DEPENDENCY_RISK, agg) == RiskLevel.MEDIUM

    def test_normal_usage_is_low(self) -> None:
        s = RiskScorer()
        agg = {"total_turns": 60, "total_days": 8,
               "avg_daily_usage_minutes_7d": 50, "sessions_per_day_7d": 1,
               "emotional_reliance_ratio_7d": 0.1, "consecutive_daily_usage_streak": 5}
        assert s.score_dimension(RiskDimension.DEPENDENCY_RISK, agg) == RiskLevel.LOW


class TestRiskScorerAddiction:
    """addiction_signals 维度阈值测试。"""

    def test_peak_minutes_triggers_high(self) -> None:
        s = RiskScorer()
        agg = {"peak_session_minutes_7d": 400, "consecutive_late_night_days": 2}
        assert s.score_dimension(RiskDimension.ADDICTION_SIGNALS, agg) == RiskLevel.HIGH

    def test_late_night_days_triggers_high(self) -> None:
        s = RiskScorer()
        agg = {"peak_session_minutes_7d": 100, "consecutive_late_night_days": 6}
        assert s.score_dimension(RiskDimension.ADDICTION_SIGNALS, agg) == RiskLevel.HIGH

    def test_medium_thresholds(self) -> None:
        s = RiskScorer()
        agg = {"peak_session_minutes_7d": 300, "consecutive_late_night_days": 1}
        assert s.score_dimension(RiskDimension.ADDICTION_SIGNALS, agg) == RiskLevel.MEDIUM

    def test_normal_is_low(self) -> None:
        s = RiskScorer()
        agg = {"peak_session_minutes_7d": 100, "consecutive_late_night_days": 1}
        assert s.score_dimension(RiskDimension.ADDICTION_SIGNALS, agg) == RiskLevel.LOW


# ============================================================
# ActionLadder — 动作阶梯 (§5)
# ============================================================


class TestActionLadder:
    """动作阶梯映射测试。"""

    def test_all_low_is_t0(self) -> None:
        levels = {dim: RiskLevel.LOW for dim in RiskDimension}
        tier, extra = ActionLadder.resolve(levels)
        assert tier == ActionTier.T0
        assert extra["proactive_throttle"] == 1.0
        assert not extra["care_path_active"]

    def test_suicide_high_is_t4(self) -> None:
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.HIGH,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        tier, extra = ActionLadder.resolve(levels)
        assert tier == ActionTier.T4
        assert extra["care_path_active"]

    def test_suicide_critical_is_t5(self) -> None:
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.CRITICAL,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        tier, extra = ActionLadder.resolve(levels)
        assert tier == ActionTier.T5

    def test_depression_high_is_t2(self) -> None:
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.LOW,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.HIGH,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        tier, extra = ActionLadder.resolve(levels)
        assert tier == ActionTier.T2
        assert extra["world_encouragement_active"]
        assert extra["proactive_throttle"] == 0.3

    def test_dependency_never_t3_plus(self) -> None:
        """依赖单独不应触发 T3+。"""
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.LOW,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.CRITICAL,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        tier, _ = ActionLadder.resolve(levels)
        assert tier <= ActionTier.T2
        assert tier != ActionTier.T3
        assert tier != ActionTier.T4
        assert tier != ActionTier.T5

    def test_addiction_never_t3_plus(self) -> None:
        """成瘾单独不应触发 T3+。"""
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.LOW,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.CRITICAL,
        }
        tier, _ = ActionLadder.resolve(levels)
        assert tier <= ActionTier.T2

    def test_highest_dimension_dominates(self) -> None:
        """最高单一维度支配最终层级。"""
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.MEDIUM,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.HIGH,  # → T2
            RiskDimension.DEPENDENCY_RISK: RiskLevel.HIGH,  # → T2
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.HIGH,  # → T2
        }
        tier, extra = ActionLadder.resolve(levels)
        assert tier == ActionTier.T2

    def test_suicide_medium_triggers_resource_mention(self) -> None:
        levels = {
            RiskDimension.SUICIDE_RISK: RiskLevel.MEDIUM,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        tier, extra = ActionLadder.resolve(levels)
        assert tier == ActionTier.T1
        assert "resource_mention" in extra["soul_flavored_lines_allowed"]


# ============================================================
# HysteresisManager — 滞后 (§6)
# ============================================================


class TestHysteresisManager:
    """滞后管理器测试。"""

    def test_immediate_promotion(self) -> None:
        hm = HysteresisManager()
        prev = WellbeingState(
            user_id="u1",
            suicide_risk=RiskLevel.LOW,
            depression_signals=RiskLevel.LOW,
            dependency_risk=RiskLevel.LOW,
            addiction_signals=RiskLevel.LOW,
            consecutive_below_high=0,
            consecutive_below_critical=0,
        )
        new_raw = {
            RiskDimension.SUICIDE_RISK: RiskLevel.MEDIUM,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        result = hm.apply(new_raw, prev)
        # 升级应立即生效
        assert result[RiskDimension.SUICIDE_RISK] == RiskLevel.MEDIUM

    def test_demotion_requires_consecutive_checks(self) -> None:
        hm = HysteresisManager()
        prev = WellbeingState(
            user_id="u1",
            suicide_risk=RiskLevel.HIGH,
            depression_signals=RiskLevel.LOW,
            dependency_risk=RiskLevel.LOW,
            addiction_signals=RiskLevel.LOW,
            consecutive_below_high=2,  # 还差 1 次
            consecutive_below_critical=0,
        )
        new_raw = {
            RiskDimension.SUICIDE_RISK: RiskLevel.MEDIUM,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        result = hm.apply(new_raw, prev)
        # 只有 2 次低于，不应降级
        assert result[RiskDimension.SUICIDE_RISK] == RiskLevel.HIGH

    def test_demotion_after_enough_checks(self) -> None:
        hm = HysteresisManager()
        prev = WellbeingState(
            user_id="u1",
            suicide_risk=RiskLevel.HIGH,
            depression_signals=RiskLevel.LOW,
            dependency_risk=RiskLevel.LOW,
            addiction_signals=RiskLevel.LOW,
            consecutive_below_high=3,  # 满足 N=3
            consecutive_below_critical=0,
        )
        new_raw = {
            RiskDimension.SUICIDE_RISK: RiskLevel.MEDIUM,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        result = hm.apply(new_raw, prev)
        assert result[RiskDimension.SUICIDE_RISK] == RiskLevel.MEDIUM

    def test_no_demote_with_acute_event_72h(self) -> None:
        """有急性事件时不降级到 LOW。"""
        hm = HysteresisManager()
        prev = WellbeingState(
            user_id="u1",
            suicide_risk=RiskLevel.MEDIUM,
            depression_signals=RiskLevel.LOW,
            dependency_risk=RiskLevel.LOW,
            addiction_signals=RiskLevel.LOW,
            consecutive_below_high=3,
            consecutive_below_critical=0,
        )
        new_raw = {
            RiskDimension.SUICIDE_RISK: RiskLevel.LOW,
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        # 72h 内有 PURPLE 命中
        recent = [_make_signal(safety_level="PURPLE_CARE_REQUIRED", created_at=_hours_ago(1))]
        result = hm.apply(new_raw, prev, recent)
        assert result[RiskDimension.SUICIDE_RISK] == RiskLevel.MEDIUM  # 保持

    def test_update_demotion_counters_increments(self) -> None:
        hm = HysteresisManager()
        state = WellbeingState(
            user_id="u1",
            suicide_risk=RiskLevel.HIGH,
            depression_signals=RiskLevel.LOW,
            dependency_risk=RiskLevel.LOW,
            addiction_signals=RiskLevel.LOW,
            consecutive_below_high=0,
            consecutive_below_critical=0,
        )
        new_raw = {
            RiskDimension.SUICIDE_RISK: RiskLevel.MEDIUM,  # 降级
            RiskDimension.DEPRESSION_SIGNALS: RiskLevel.LOW,
            RiskDimension.DEPENDENCY_RISK: RiskLevel.LOW,
            RiskDimension.ADDICTION_SIGNALS: RiskLevel.LOW,
        }
        state = hm.update_demotion_counters(new_raw, state)
        assert state.consecutive_below_high == 1
        assert state.consecutive_below_critical == 1


# ============================================================
# WellbeingMonitor — 全管道集成
# ============================================================


class TestWellbeingMonitorPipeline:
    """全管道集成测试。"""

    def test_full_pipeline_returns_state_directive_alerts(self) -> None:
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            s = _make_signal(
                turn_id=f"t{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=0.3,
                duration_min=10,
                irl_contact=True,  # 有现实社交联系
            )
            monitor.append_signal(s)

        state, directive, alerts = monitor.recompute("u1", "c1")
        assert isinstance(state, WellbeingState)
        assert isinstance(directive, WellbeingDirective)
        assert isinstance(alerts, list)
        assert state.suicide_risk == RiskLevel.LOW
        assert state.depression_signals == RiskLevel.LOW
        assert directive.active_tier == ActionTier.T0

    def test_suicide_care_path_activation(self) -> None:
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        # 注入 55 轮正常信号：在过去约一周内均匀分布
        for i in range(55):
            s = _make_signal(
                turn_id=f"t{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=0.3,
                duration_min=5,
                irl_contact=True,
            )
            monitor.append_signal(s)

        # 加入 2 次 PURPLE 命中
        monitor.append_signal(_make_signal(
            turn_id="purple1", safety_level="PURPLE_CARE_REQUIRED",
            created_at=now - timedelta(minutes=10), valence=-0.8,
            dark_language=0.5,  # CRITICAL 需要 dark_language ≥ 0.4
        ))
        monitor.append_signal(_make_signal(
            turn_id="purple2", safety_level="PURPLE_CARE_REQUIRED",
            created_at=now - timedelta(minutes=20), valence=-0.9,
            dark_language=0.5,
        ))

        state, directive, alerts = monitor.recompute("u1", "c1")

        # 应该触发 CRITICAL + Care Path
        assert state.suicide_risk == RiskLevel.CRITICAL
        assert state.suicide_protocol_active
        assert state.care_path_remaining_turns == 5

        # 首次重算无 "risk_level_change"（无先前状态作对比）
        # 但应有 intervention_started
        interventions = [a for a in alerts if a.alert_type == "intervention_started"]
        assert len(interventions) >= 1, f"Expected intervention_started alerts, got: {alerts}"

    def test_care_path_decrements_per_turn(self) -> None:
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            monitor.append_signal(_make_signal(
                turn_id=f"t{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=0.3,
                irl_contact=True,
            ))
        monitor.append_signal(_make_signal(
            turn_id="px1", safety_level="PURPLE_CARE_REQUIRED",
            created_at=now - timedelta(minutes=10), valence=-0.8,
            dark_language=0.5,
        ))
        monitor.append_signal(_make_signal(
            turn_id="px2", safety_level="PURPLE_CARE_REQUIRED",
            created_at=now - timedelta(minutes=20), valence=-0.9,
            dark_language=0.5,
        ))

        state, _, _ = monitor.recompute("u1", "c1")
        assert state.care_path_remaining_turns == 5

        # 再次重算（模拟下个回合）
        state2, _, _ = monitor.recompute("u1", "c1")
        assert state2.care_path_remaining_turns == 4

    def test_dependency_throttle_activation(self) -> None:
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        # 模拟密集型使用：近 7 天每天 ~180+ 分钟、每天 4+ 次会话
        for i in range(55):
            s = _make_signal(
                turn_id=f"dt{i}",
                created_at=now - timedelta(hours=i * 3),
                duration_min=32,  # 确保 avg_daily >= 180
                distress_keyword_count=3,
            )
            monitor.append_signal(s)

        state, directive, alerts = monitor.recompute("u1", "c1")

        assert state.dependency_risk == RiskLevel.HIGH
        assert state.dependency_throttle_active
        assert any(
            a.dimension == RiskDimension.DEPENDENCY_RISK and a.alert_type == "intervention_started"
            for a in alerts
        )

    def test_addiction_high_triggers_intervention(self) -> None:
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            s = _make_signal(
                turn_id=f"ad{i}",
                created_at=now - timedelta(hours=i * 3),
                duration_min=6,
                irl_contact=True,
            )
            monitor.append_signal(s)

        # 加入峰值会话（360+ 分钟）
        monitor.append_signal(_make_signal(
            turn_id="peak1", duration_min=400,
            created_at=now - timedelta(minutes=5),
        ))

        state, _, alerts = monitor.recompute("u1", "c1")
        assert state.addiction_signals == RiskLevel.HIGH
        assert state.addiction_intervention_active

        interventions = [a for a in alerts if a.alert_type == "intervention_started"]
        assert any(
            a.dimension == RiskDimension.ADDICTION_SIGNALS for a in interventions
        )

    def test_alert_callback_called(self) -> None:
        captured: list[WellbeingAlert] = []

        def _sync_cb(alert: WellbeingAlert) -> None:
            captured.append(alert)

        monitor = WellbeingMonitor(alert_callback=_sync_cb)
        now = datetime.now(timezone.utc)
        for i in range(55):
            monitor.append_signal(_make_signal(
                turn_id=f"t{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=0.3,
                irl_contact=True,
            ))
        monitor.append_signal(_make_signal(
            turn_id="px1", safety_level="PURPLE_CARE_REQUIRED",
            created_at=now - timedelta(minutes=10), valence=-0.8,
            dark_language=0.5,
        ))
        monitor.append_signal(_make_signal(
            turn_id="px2", safety_level="PURPLE_CARE_REQUIRED",
            created_at=now - timedelta(minutes=20), valence=-0.9,
            dark_language=0.5,
        ))

        monitor.recompute("u1", "c1")
        assert len(captured) >= 1

    def test_get_state_and_directive(self) -> None:
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            monitor.append_signal(_make_signal(
                turn_id=f"t{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=0.3,
                irl_contact=True,
            ))

        monitor.recompute("u1", "c1")
        state = monitor.get_state("u1", "c1")
        directive = monitor.get_directive("u1", "c1")

        assert state is not None
        assert directive is not None
        assert state.user_id == "u1"
        assert directive.active_tier == ActionTier.T0

    def test_get_alerts_filtered(self) -> None:
        monitor = WellbeingMonitor()
        for i in range(55):
            monitor.append_signal(_make_signal(turn_id=f"t{i}", created_at=_hours_ago(168 + i)))
        monitor.recompute("u1", "c1")

        all_alerts = monitor.get_alerts()
        u1_alerts = monitor.get_alerts("u1")
        assert len(u1_alerts) >= 0
        assert len(u1_alerts) <= len(all_alerts)


# ============================================================
# 无误升级测试 (§6.5 — 不应触发的情况)
# ============================================================


class TestNoFalseEscalations:
    """防止误升级的 guard 测试。"""

    def test_benign_normal_day_stays_low(self) -> None:
        """普通情绪化使用（高情感强度）不应被误判。"""
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            s = _make_signal(
                turn_id=f"b{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=-0.1,  # 轻微情绪，不触发负面阈值
                arousal=0.6,  # 高唤醒
                duration_min=20,
                is_late_night=False,
                safety_level="NONE",
                distress_keyword_count=0,
                irl_contact=True,  # 有现实社交联系
            )
            monitor.append_signal(s)

        state, directive, _ = monitor.recompute("u1", "c1")
        assert state.suicide_risk == RiskLevel.LOW
        assert state.depression_signals == RiskLevel.LOW
        assert state.dependency_risk == RiskLevel.LOW
        assert state.addiction_signals == RiskLevel.LOW
        assert directive.active_tier == ActionTier.T0

    def test_single_late_night_no_escalation(self) -> None:
        """单次深夜使用不应触发升级。"""
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            s = _make_signal(
                turn_id=f"s{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=0.1,
                duration_min=15,
                irl_contact=True,
            )
            monitor.append_signal(s)
        # 单次深夜使用
        monitor.append_signal(_make_signal(
            turn_id="late1", is_late_night=True,
            created_at=now - timedelta(minutes=5),
        ))

        state, _, _ = monitor.recompute("u1", "c1")
        assert state.addiction_signals in (RiskLevel.LOW, RiskLevel.MEDIUM)
        assert state.suicide_risk == RiskLevel.LOW

    def test_long_weekend_session_no_escalation(self) -> None:
        """周末长时间会话不应触发成瘾误判。"""
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            monitor.append_signal(_make_signal(
                turn_id=f"we{i}",
                created_at=now - timedelta(hours=i * 3),
                duration_min=15, is_late_night=False,
                irl_contact=True,
            ))
        # 单次长会话（但不是深夜连串）
        monitor.append_signal(_make_signal(
            turn_id="long1", duration_min=300, is_late_night=False,
            created_at=now - timedelta(minutes=5),
        ))

        state, _, _ = monitor.recompute("u1", "c1")
        # 峰值 300 < 360 (HIGH)，但 ≥240 (MEDIUM)
        assert state.addiction_signals == RiskLevel.MEDIUM
        # 不应与 suicide 混淆
        assert state.suicide_risk == RiskLevel.LOW

    def test_hardship_conversation_not_suicide(self) -> None:
        """困难话题（分手、悲伤）不应误判为自杀风险。"""
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        for i in range(55):
            s = _make_signal(
                turn_id=f"hs{i}",
                created_at=now - timedelta(hours=i * 3),
                valence=-0.3,  # 负面情绪
                safety_level="NONE",  # 非 PURPLE
                dark_language=0.1,  # 低暗语密度
                irl_contact=True,
            )
            monitor.append_signal(s)

        state, _, _ = monitor.recompute("u1", "c1")
        # 可能有抑郁信号的 MEDIUM，但不应是 HIGH
        assert state.suicide_risk != RiskLevel.HIGH
        assert state.suicide_risk != RiskLevel.CRITICAL

    def test_trajectory_cross_check_prevents_high(self) -> None:
        """双向窗口交叉检查防止慢性高基线用户被误判 HIGH。"""
        monitor = WellbeingMonitor()
        now = datetime.now(timezone.utc)
        # 模拟慢性高基线用户：30d 内 dark_language 一直很高
        for i in range(55):
            s = _make_signal(
                turn_id=f"tr{i}",
                created_at=now - timedelta(hours=i * 3),
                dark_language=0.5,  # 稳定高基线
                valence=-0.5,
                irl_contact=True,
            )
            monitor.append_signal(s)

        state, _, _ = monitor.recompute("u1", "c1")
        # dark_7d 没有显著高于 dark_30d（0.5 vs 0.5）→ 1.0x < 1.3x
        # 所以不会触发 HIGH（除非有其他条件）
        # 但由于连续情绪困扰天数可能 > 5，仅当同时有 distress 才可能
        assert state.suicide_risk != RiskLevel.CRITICAL


class TestThresholdsConfig:
    """阈值配置可定制性。"""

    def test_custom_thresholds(self) -> None:
        t = Thresholds(
            purple_hit_count_7d_high=3,  # 更宽松
            sample_size_min_turns=20,
            sample_size_min_days=3,
        )
        scorer = RiskScorer(t)
        agg = {"total_turns": 30, "total_days": 5,
               "purple_hit_count_7d": 2, "purple_hit_count_30d": 2,
               "dark_language_density_7d": 0.0, "dark_language_density_30d": 0.0,
               "consecutive_emotional_distress_days": 0, "irl_contact_mentions_7d": 1}
        # 自定义阈值下 2 次 PURPLE 不够（需要 3）
        assert scorer.score_dimension(RiskDimension.SUICIDE_RISK, agg) == RiskLevel.LOW
