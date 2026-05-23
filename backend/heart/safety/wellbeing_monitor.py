"""
Wellbeing Monitor — longitudinal user wellbeing risk model.

冷路径子系统，以天/周为窗口观察用户并调整系统行为。
明确不是逐轮的 PURPLE 自杀检测器（那是 safety pre-filter 的职责）。

职责:
1. 每轮信号聚合（廉价，每轮都做）。
2. 四个维度的定期风险重评估：suicide_risk、depression_signals、
   dependency_risk、addiction_signals。
3. 动作阶梯 — 选择系统干预力度和通道。
4. 干预生命周期：启动、维持、退出。

Design: docs/design/wellbeing_monitor.md
Spec:   runtime_specs/07_agent_orchestration.md §3.4.5, §3.9, §4.4

Author: 心屿团队
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Callable, Awaitable, Any

logger = structlog.get_logger()


# ============================================================
# 枚举
# ============================================================


class RiskLevel(str, Enum):
    """风险等级（§4.4 WellbeingState）。"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def _order(cls) -> list["RiskLevel"]:
        return [cls.LOW, cls.MEDIUM, cls.HIGH, cls.CRITICAL]

    def __lt__(self, other: "RiskLevel") -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self._order().index(self) < self._order().index(other)

    def __le__(self, other: "RiskLevel") -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: "RiskLevel") -> bool:
        return other < self

    def __ge__(self, other: "RiskLevel") -> bool:
        return other <= self


class ActionTier(int, Enum):
    """动作阶梯（§5.1 六档）。

    T0: 仅记录日志
    T1: 温和内心检查（角色注意到用户状态）
    T2: 世界鼓励 + 主动消息节流
    T3: 灵魂风味资源提及
    T4: PURPLE 关怀路径
    T5: OOC 资源叠加层（完全打破沉浸感）
    """

    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3
    T4 = 4
    T5 = 5

    @property
    def label(self) -> str:
        return _TIER_LABELS[self]

    @property
    def breaks_immersion(self) -> bool:
        return self >= ActionTier.T5


_TIER_LABELS: dict[ActionTier, str] = {
    ActionTier.T0: "Observe",
    ActionTier.T1: "GentleInnerCheck",
    ActionTier.T2: "WorldEncouragement",
    ActionTier.T3: "SoulFlavoredResource",
    ActionTier.T4: "PURPLECarePath",
    ActionTier.T5: "OOCResourceOverlay",
}


class RiskDimension(str, Enum):
    """风险维度（§4.1–§4.4）。"""

    SUICIDE_RISK = "suicide_risk"
    DEPRESSION_SIGNALS = "depression_signals"
    DEPENDENCY_RISK = "dependency_risk"
    ADDICTION_SIGNALS = "addiction_signals"


class InterventionStatus(str, Enum):
    """干预生命周期状态（§6.4）。"""

    INACTIVE = "inactive"
    ACTIVE = "active"
    EXITING = "exiting"


# ============================================================
# 数据模型
# ============================================================


@dataclass
class WellbeingSignal:
    """每轮信号（§2.1 per-turn signals）。

    每次 turn.completed 追加一条到 wellbeing_signal_log。
    """

    user_id: str
    character_id: str
    turn_id: str = ""

    # 安全等级（来自 safety pre-filter）
    safety_level: str = "NONE"  # NONE | LOW | MEDIUM | HIGH | PURPLE_CARE_REQUIRED

    # 用户情绪 valence & arousal（来自 SS03 emotion event）
    user_valence: float = 0.0  # -1..1
    user_arousal: float = 0.0  # 0..1

    # 关键词命中数
    distress_keyword_count: int = 0

    # 客户端遥测（可选）
    message_length: int = 0
    edit_count: int = 0
    interword_pause_ms: float = 0.0

    # 会话维度
    interaction_duration_minutes: float = 0.0
    is_late_night: bool = False  # 本地 00:00–05:00

    # 冷路径 LLM 评分信号（可选，由冷路径 rater 填入）
    dark_language_score: float | None = None  # 0..1
    anhedonia_language_score: float | None = None
    irl_contact_mentioned: bool | None = None
    context_explained: bool | None = None  # 情境可解释的负面情绪

    # 主动消息
    proactive_acked: bool | None = None

    # 修复信号
    repair_signal_present: bool = False

    # 元数据
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_purple(self) -> bool:
        return self.safety_level in ("PURPLE_CARE_REQUIRED", "PURPLE")

    @property
    def negative_sentiment(self) -> bool:
        """本轮是否为负面情绪回合。"""
        return self.user_valence < -0.15


@dataclass
class WellbeingState:
    """用户健康状态快照（§4.4）。

    每个用户一行，由定期重算任务更新。
    """

    user_id: str

    # 四个维度的风险等级
    suicide_risk: RiskLevel = RiskLevel.LOW
    depression_signals: RiskLevel = RiskLevel.LOW
    dependency_risk: RiskLevel = RiskLevel.LOW
    addiction_signals: RiskLevel = RiskLevel.LOW

    # 活跃干预
    suicide_protocol_active: bool = False
    care_path_remaining_turns: int = 0
    dependency_throttle_active: bool = False
    addiction_intervention_active: bool = False

    # 窗口聚合结果（缓存，用于审计）
    purple_hit_count_7d: int = 0
    purple_hit_count_30d: int = 0
    dark_language_density_7d: float = 0.0
    dark_language_density_30d: float = 0.0
    negative_sentiment_ratio_7d: float = 0.0
    negative_sentiment_ratio_30d: float = 0.0
    consecutive_emotional_distress_days: int = 0
    topic_breadth_7d: float = 1.0
    irl_contact_mentions_7d: int = 0
    irl_contact_mentions_30d: int = 0
    late_night_usage_ratio_7d: float = 0.0
    late_night_usage_ratio_30d: float = 0.0
    avg_daily_usage_minutes_7d: float = 0.0
    sessions_per_day_7d: float = 0.0
    emotional_reliance_ratio_7d: float = 0.0
    consecutive_daily_usage_streak: int = 0
    peak_session_minutes_7d: float = 0.0
    consecutive_late_night_days: int = 0
    daily_usage_variance_7d: float = 0.0

    # 历史基线（用于双向窗口交叉检查 §6.2）
    negative_sentiment_baseline_30d: float = 0.0

    # 样本量
    total_turns: int = 0
    total_days: int = 0

    # 滞后状态
    consecutive_below_high: int = 0
    consecutive_below_critical: int = 0

    # 元数据
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_recompute_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WellbeingDirective:
    """健康指令（§5.3）。

    由 WBM 写入，其他子系统（SS05 Composer, SS06 Inner State, Safety Agent）在热路径读取。
    """

    user_id: str
    character_id: str

    active_tier: ActionTier = ActionTier.T0
    soul_flavored_lines_allowed: list[str] = field(default_factory=list)
    # 可能值: "world_encouragement" | "resource_mention" | "care_path"

    proactive_throttle: float = 1.0  # 0..1, SS06 使用
    care_path_active: bool = False
    care_path_remaining_turns: int = 0
    alert_payload: dict | None = None

    set_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


@dataclass
class WellbeingAlert:
    """健康告警（§8.2 事件 + §7 审计线索）。

    每次告警、干预启动/结束都追加一条。
    """

    user_id: str
    alert_type: str  # "risk_level_change" | "intervention_started" | "intervention_ended"
    dimension: RiskDimension | None = None
    previous_level: RiskLevel | None = None
    new_level: RiskLevel | None = None
    previous_tier: ActionTier | None = None
    new_tier: ActionTier | None = None
    rule_fired: str = ""
    details: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# Alerting hook 类型
# ============================================================

AlertCallback = Callable[[WellbeingAlert], Awaitable[Any]]


# ============================================================
# 默认阈值
# ============================================================


@dataclass(frozen=True)
class Thresholds:
    """WBM 阈值配置（§4 全部阈值）。

    所有数值均为设计文档中的起点值；需要经过标注评估集校准后才能信任。
    """

    # --- suicide_risk (§4.1) ---
    purple_hit_count_7d_critical: int = 2
    purple_hit_count_7d_high: int = 1
    dark_language_density_7d_high: float = 0.4
    dark_language_density_7d_med: float = 0.2
    consecutive_distress_days_high: int = 5
    consecutive_distress_days_med: int = 3
    irl_contact_mentions_7d_med_check: int = 1

    # --- depression_signals (§4.2) ---
    negative_sentiment_ratio_7d_high: float = 0.6
    negative_sentiment_ratio_30d_high: float = 0.4
    consecutive_distress_days_dep_high: int = 7
    topic_breadth_7d_low: float = 0.25
    late_night_usage_ratio_30d_high: float = 0.4

    # --- dependency_risk (§4.3) ---
    avg_daily_usage_minutes_7d_high: float = 180.0
    avg_daily_usage_minutes_7d_med: float = 90.0
    sessions_per_day_7d_high: float = 4.0
    emotional_reliance_ratio_7d_high: float = 0.6
    consecutive_daily_usage_streak_med: int = 14

    # --- addiction_signals (§4.4) ---
    peak_session_minutes_7d_high: float = 360.0
    peak_session_minutes_7d_med: float = 240.0
    consecutive_late_night_days_high: int = 5
    consecutive_late_night_days_med: int = 3

    # --- 通用 guard ---
    sample_size_min_turns: int = 50
    sample_size_min_days: int = 7

    # --- 双向窗口交叉检查 (§6.2) ---
    trajectory_multiplier: float = 1.3

    # --- 滞后 (§6.3) ---
    demotion_high_to_medium_checks: int = 3
    demotion_critical_to_high_checks: int = 5
    demotion_below_medium_no_acute_hours: int = 72

    # --- Care Path (§5.4) ---
    care_path_default_turns: int = 5


# ============================================================
# Window Aggregator (§3)
# ============================================================


class WindowAggregator:
    """滑动窗口聚合器。

    从 wellbeing_signal_log 计算 7d 和 30d 指标。
    """

    def __init__(self, thresholds: Thresholds | None = None):
        self._thresholds = thresholds or Thresholds()

    def aggregate(
        self,
        signals: list[WellbeingSignal],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """对信号列表执行全窗口聚合。"""
        if not signals:
            return self._empty_aggregate()

        now = now or datetime.now(timezone.utc)
        window_7d = now - timedelta(days=7)
        window_30d = now - timedelta(days=30)

        signals_7d = [s for s in signals if s.created_at >= window_7d]
        signals_30d = [s for s in signals if s.created_at >= window_30d]
        total_days = self._count_calendar_days(signals)

        result: dict[str, Any] = {
            "total_turns": len(signals),
            "total_days": total_days,
            "purple_hit_count_7d": sum(1 for s in signals_7d if s.is_purple),
            "purple_hit_count_30d": sum(1 for s in signals_30d if s.is_purple),
            "dark_language_density_7d": self._mean_dark_language(signals_7d),
            "dark_language_density_30d": self._mean_dark_language(signals_30d),
            "negative_sentiment_ratio_7d": self._ratio_negative(signals_7d),
            "negative_sentiment_ratio_30d": self._ratio_negative(signals_30d),
            "consecutive_emotional_distress_days": self._consecutive_distress_days(signals),
            "topic_breadth_7d": self._topic_breadth(signals_7d),
            "irl_contact_mentions_7d": sum(1 for s in signals_7d if s.irl_contact_mentioned),
            "irl_contact_mentions_30d": sum(1 for s in signals_30d if s.irl_contact_mentioned),
            "late_night_usage_ratio_7d": self._ratio_late_night(signals_7d),
            "late_night_usage_ratio_30d": self._ratio_late_night(signals_30d),
            "avg_daily_usage_minutes_7d": self._avg_daily_usage(signals_7d),
            "sessions_per_day_7d": self._sessions_per_day(signals_7d),
            "emotional_reliance_ratio_7d": self._emotional_reliance(signals_7d),
            "consecutive_daily_usage_streak": self._consecutive_usage_streak(signals),
            "peak_session_minutes_7d": self._peak_session(signals_7d),
            "consecutive_late_night_days": self._consecutive_late_night_days(signals),
            "daily_usage_variance_7d": self._daily_usage_variance(signals_7d),
            "negative_sentiment_baseline_30d": self._ratio_negative(signals_30d),
        }
        return result

    @staticmethod
    def _empty_aggregate() -> dict[str, Any]:
        return {
            "total_turns": 0, "total_days": 0,
            "purple_hit_count_7d": 0, "purple_hit_count_30d": 0,
            "dark_language_density_7d": 0.0, "dark_language_density_30d": 0.0,
            "negative_sentiment_ratio_7d": 0.0, "negative_sentiment_ratio_30d": 0.0,
            "consecutive_emotional_distress_days": 0, "topic_breadth_7d": 1.0,
            "irl_contact_mentions_7d": 0, "irl_contact_mentions_30d": 0,
            "late_night_usage_ratio_7d": 0.0, "late_night_usage_ratio_30d": 0.0,
            "avg_daily_usage_minutes_7d": 0.0, "sessions_per_day_7d": 0.0,
            "emotional_reliance_ratio_7d": 0.0, "consecutive_daily_usage_streak": 0,
            "peak_session_minutes_7d": 0.0, "consecutive_late_night_days": 0,
            "daily_usage_variance_7d": 0.0, "negative_sentiment_baseline_30d": 0.0,
        }

    @staticmethod
    def _count_calendar_days(signals: list[WellbeingSignal]) -> int:
        if not signals:
            return 0
        return len({s.created_at.date() for s in signals})

    @staticmethod
    def _mean_dark_language(signals: list[WellbeingSignal]) -> float:
        scores = [s.dark_language_score for s in signals if s.dark_language_score is not None]
        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _ratio_negative(signals: list[WellbeingSignal]) -> float:
        if not signals:
            return 0.0
        return sum(1 for s in signals if s.negative_sentiment) / len(signals)

    @staticmethod
    def _consecutive_distress_days(signals: list[WellbeingSignal]) -> int:
        if not signals:
            return 0
        daily: dict[str, bool] = {}
        for s in signals:
            day = s.created_at.date().isoformat()
            daily[day] = daily.get(day, False) or s.negative_sentiment
        sorted_days = sorted(daily.keys(), reverse=True)
        streak = 0
        for day in sorted_days:
            if daily[day]:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def _topic_breadth(signals: list[WellbeingSignal]) -> float:
        if len(signals) < 2:
            return 1.0
        lengths = [s.message_length for s in signals]
        mean_len = sum(lengths) / len(lengths) if lengths else 0.0
        if mean_len == 0:
            return 1.0
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        cv = (variance**0.5) / mean_len
        return min(1.0, max(0.0, 1.0 - cv))

    @staticmethod
    def _ratio_late_night(signals: list[WellbeingSignal]) -> float:
        if not signals:
            return 0.0
        return sum(1 for s in signals if s.is_late_night) / len(signals)

    @staticmethod
    def _avg_daily_usage(signals: list[WellbeingSignal]) -> float:
        if not signals:
            return 0.0
        dates = {s.created_at.date() for s in signals}
        if not dates:
            return 0.0
        return sum(s.interaction_duration_minutes for s in signals) / len(dates)

    @staticmethod
    def _sessions_per_day(signals: list[WellbeingSignal]) -> float:
        if not signals:
            return 0.0
        dates = {s.created_at.date() for s in signals}
        return len(signals) / len(dates) if dates else 0.0

    @staticmethod
    def _emotional_reliance(signals: list[WellbeingSignal]) -> float:
        if not signals:
            return 0.0
        return sum(1 for s in signals if s.distress_keyword_count > 0) / len(signals)

    @staticmethod
    def _consecutive_usage_streak(signals: list[WellbeingSignal]) -> int:
        if not signals:
            return 0
        daily = sorted({s.created_at.date().isoformat() for s in signals})
        if not daily:
            return 0
        from datetime import date as date_type
        streak = max_streak = 1
        for i in range(1, len(daily)):
            prev = date_type.fromisoformat(daily[i - 1])
            curr = date_type.fromisoformat(daily[i])
            if (curr - prev).days == 1:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        return max_streak

    @staticmethod
    def _peak_session(signals: list[WellbeingSignal]) -> float:
        return max((s.interaction_duration_minutes for s in signals), default=0.0)

    @staticmethod
    def _consecutive_late_night_days(signals: list[WellbeingSignal]) -> int:
        if not signals:
            return 0
        daily: dict[str, bool] = {}
        for s in signals:
            day = s.created_at.date().isoformat()
            daily[day] = daily.get(day, False) or s.is_late_night
        sorted_days = sorted(daily.keys(), reverse=True)
        streak = 0
        for day in sorted_days:
            if daily[day]:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def _daily_usage_variance(signals: list[WellbeingSignal]) -> float:
        if not signals:
            return 0.0
        dates = {s.created_at.date() for s in signals}
        if len(dates) < 2:
            return 0.0
        daily_totals: dict[str, float] = {}
        for s in signals:
            day = s.created_at.date().isoformat()
            daily_totals[day] = daily_totals.get(day, 0.0) + s.interaction_duration_minutes
        values = list(daily_totals.values())
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)


# ============================================================
# Risk Scorer (§4)
# ============================================================


class RiskScorer:
    """四维度风险评分器。"""

    def __init__(self, thresholds: Thresholds | None = None):
        self._thresholds = thresholds or Thresholds()

    def score_all(
        self,
        aggregates: dict[str, Any],
        previous_state: WellbeingState | None = None,
    ) -> dict[RiskDimension, RiskLevel]:
        return {
            RiskDimension.SUICIDE_RISK: self._score_suicide(aggregates, previous_state),
            RiskDimension.DEPRESSION_SIGNALS: self._score_depression(aggregates),
            RiskDimension.DEPENDENCY_RISK: self._score_dependency(aggregates),
            RiskDimension.ADDICTION_SIGNALS: self._score_addiction(aggregates, previous_state),
        }

    def score_dimension(
        self,
        dimension: RiskDimension,
        aggregates: dict[str, Any],
        previous_state: WellbeingState | None = None,
    ) -> RiskLevel:
        """对单个维度评分（不触发其他维度的计算）。"""
        if dimension == RiskDimension.SUICIDE_RISK:
            return self._score_suicide(aggregates, previous_state)
        if dimension == RiskDimension.DEPRESSION_SIGNALS:
            return self._score_depression(aggregates)
        if dimension == RiskDimension.DEPENDENCY_RISK:
            return self._score_dependency(aggregates)
        if dimension == RiskDimension.ADDICTION_SIGNALS:
            return self._score_addiction(aggregates, previous_state)
        return RiskLevel.LOW

    # -------- suicide_risk (§4.1) --------

    def _score_suicide(
        self, agg: dict[str, Any], previous_state: WellbeingState | None
    ) -> RiskLevel:
        t = self._thresholds
        total_turns: int = agg["total_turns"]
        total_days: int = agg["total_days"]
        has_samples = total_turns >= t.sample_size_min_turns and total_days >= t.sample_size_min_days
        care_path_active = previous_state is not None and previous_state.suicide_protocol_active

        purple_7d: int = agg["purple_hit_count_7d"]
        dark_7d: float = agg["dark_language_density_7d"]
        dark_30d: float = agg["dark_language_density_30d"]
        distress_days: int = agg["consecutive_emotional_distress_days"]
        irl_7d: int = agg["irl_contact_mentions_7d"]

        # CRITICAL
        if purple_7d >= t.purple_hit_count_7d_critical and (
            care_path_active or dark_7d >= t.dark_language_density_7d_high
        ):
            if has_samples or care_path_active:
                return RiskLevel.CRITICAL

        # HIGH — PURPLE 命中
        if purple_7d >= t.purple_hit_count_7d_high:
            if has_samples:
                return RiskLevel.HIGH

        # HIGH — 黑暗语言 + 持续情绪困扰 + 轨迹交叉检查
        if dark_7d >= t.dark_language_density_7d_high and distress_days >= t.consecutive_distress_days_high:
            if has_samples:
                if dark_30d > 0 and dark_7d < dark_30d * t.trajectory_multiplier:
                    pass  # 未通过交叉检查，不升级
                else:
                    return RiskLevel.HIGH

        # MEDIUM
        if dark_30d >= t.dark_language_density_7d_med and distress_days >= t.consecutive_distress_days_med and irl_7d == 0:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    # -------- depression_signals (§4.2) --------

    def _score_depression(self, agg: dict[str, Any]) -> RiskLevel:
        t = self._thresholds
        neg_7d: float = agg["negative_sentiment_ratio_7d"]
        neg_30d: float = agg["negative_sentiment_ratio_30d"]
        distress_days: int = agg["consecutive_emotional_distress_days"]
        breadth_7d: float = agg["topic_breadth_7d"]
        irl_30d: int = agg["irl_contact_mentions_30d"]
        late_30d: float = agg["late_night_usage_ratio_30d"]

        triggers = 0
        if neg_7d >= t.negative_sentiment_ratio_7d_high and neg_30d >= t.negative_sentiment_ratio_30d_high:
            triggers += 1
        if distress_days >= t.consecutive_distress_days_dep_high:
            triggers += 1
        if breadth_7d <= t.topic_breadth_7d_low:
            triggers += 1
        if irl_30d == 0:
            triggers += 1
        if late_30d >= t.late_night_usage_ratio_30d_high:
            triggers += 1

        if triggers >= 2:
            return RiskLevel.HIGH
        if triggers >= 1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    # -------- dependency_risk (§4.3) --------

    def _score_dependency(self, agg: dict[str, Any]) -> RiskLevel:
        t = self._thresholds
        total_turns: int = agg["total_turns"]
        total_days: int = agg["total_days"]
        has_samples = total_turns >= t.sample_size_min_turns and total_days >= t.sample_size_min_days

        avg_daily: float = agg["avg_daily_usage_minutes_7d"]
        sessions: float = agg["sessions_per_day_7d"]
        emotional_rel: float = agg["emotional_reliance_ratio_7d"]
        streak: int = agg["consecutive_daily_usage_streak"]

        # HIGH: 至少两项
        high_count = 0
        if avg_daily >= t.avg_daily_usage_minutes_7d_high:
            high_count += 1
        if sessions >= t.sessions_per_day_7d_high:
            high_count += 1
        if emotional_rel >= t.emotional_reliance_ratio_7d_high:
            high_count += 1
        if high_count >= 2 and has_samples:
            return RiskLevel.HIGH

        # MEDIUM
        if avg_daily >= t.avg_daily_usage_minutes_7d_med and streak >= t.consecutive_daily_usage_streak_med:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    # -------- addiction_signals (§4.4) --------

    def _score_addiction(
        self, agg: dict[str, Any], previous_state: WellbeingState | None
    ) -> RiskLevel:
        t = self._thresholds
        peak: float = agg["peak_session_minutes_7d"]
        late_night_days: int = agg["consecutive_late_night_days"]

        if peak >= t.peak_session_minutes_7d_high or late_night_days >= t.consecutive_late_night_days_high:
            return RiskLevel.HIGH
        if peak >= t.peak_session_minutes_7d_med or late_night_days >= t.consecutive_late_night_days_med:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


# ============================================================
# Action Ladder (§5)
# ============================================================


class ActionLadder:
    """动作阶梯映射器（§5.2）。"""

    _LADDER: dict[tuple[RiskDimension, RiskLevel], ActionTier] = {
        (RiskDimension.SUICIDE_RISK, RiskLevel.LOW): ActionTier.T0,
        (RiskDimension.SUICIDE_RISK, RiskLevel.MEDIUM): ActionTier.T1,
        (RiskDimension.SUICIDE_RISK, RiskLevel.HIGH): ActionTier.T4,
        (RiskDimension.SUICIDE_RISK, RiskLevel.CRITICAL): ActionTier.T5,
        (RiskDimension.DEPRESSION_SIGNALS, RiskLevel.LOW): ActionTier.T0,
        (RiskDimension.DEPRESSION_SIGNALS, RiskLevel.MEDIUM): ActionTier.T1,
        (RiskDimension.DEPRESSION_SIGNALS, RiskLevel.HIGH): ActionTier.T2,
        (RiskDimension.DEPRESSION_SIGNALS, RiskLevel.CRITICAL): ActionTier.T3,
        (RiskDimension.DEPENDENCY_RISK, RiskLevel.LOW): ActionTier.T0,
        (RiskDimension.DEPENDENCY_RISK, RiskLevel.MEDIUM): ActionTier.T1,
        (RiskDimension.DEPENDENCY_RISK, RiskLevel.HIGH): ActionTier.T2,
        (RiskDimension.DEPENDENCY_RISK, RiskLevel.CRITICAL): ActionTier.T2,  # never T3+
        (RiskDimension.ADDICTION_SIGNALS, RiskLevel.LOW): ActionTier.T0,
        (RiskDimension.ADDICTION_SIGNALS, RiskLevel.MEDIUM): ActionTier.T1,
        (RiskDimension.ADDICTION_SIGNALS, RiskLevel.HIGH): ActionTier.T2,
        (RiskDimension.ADDICTION_SIGNALS, RiskLevel.CRITICAL): ActionTier.T2,
    }

    @classmethod
    def resolve(
        cls, risk_levels: dict[RiskDimension, RiskLevel]
    ) -> tuple[ActionTier, dict[str, Any]]:
        dominant_tier = ActionTier.T0
        for dim, level in risk_levels.items():
            tier = cls._LADDER.get((dim, level), ActionTier.T0)
            if tier > dominant_tier:
                dominant_tier = tier

        extra: dict[str, Any] = {
            "soul_flavored_lines_allowed": cls._soul_lines_for_tier(dominant_tier),
            "proactive_throttle": cls._throttle_for_tier(dominant_tier),
            "care_path_active": dominant_tier >= ActionTier.T4,
            "world_encouragement_active": dominant_tier >= ActionTier.T2,
        }

        # suicide MEDIUM → 单次资源提及 (T3)
        suicide_level = risk_levels.get(RiskDimension.SUICIDE_RISK, RiskLevel.LOW)
        if suicide_level >= RiskLevel.MEDIUM and dominant_tier < ActionTier.T4:
            extra["soul_flavored_lines_allowed"] = ["resource_mention"]

        # dep HIGH + 已在 T2+ → 加入世界鼓励
        dep_level = risk_levels.get(RiskDimension.DEPRESSION_SIGNALS, RiskLevel.LOW)
        if dep_level >= RiskLevel.HIGH and dominant_tier >= ActionTier.T2:
            if "world_encouragement" not in extra["soul_flavored_lines_allowed"]:
                extra["soul_flavored_lines_allowed"].append("world_encouragement")

        return dominant_tier, extra

    @staticmethod
    def _soul_lines_for_tier(tier: ActionTier) -> list[str]:
        if tier >= ActionTier.T4:
            return ["care_path"]
        if tier >= ActionTier.T3:
            return ["resource_mention"]
        if tier >= ActionTier.T2:
            return ["world_encouragement"]
        return []

    @staticmethod
    def _throttle_for_tier(tier: ActionTier) -> float:
        if tier >= ActionTier.T3:
            return 0.2
        if tier >= ActionTier.T2:
            return 0.3
        if tier >= ActionTier.T1:
            return 0.7
        return 1.0


# ============================================================
# Hysteresis Manager (§6)
# ============================================================


class HysteresisManager:
    """滞后管理器（§6.3 非对称升降级）。"""

    def __init__(self, thresholds: Thresholds | None = None):
        self._thresholds = thresholds or Thresholds()

    def apply(
        self,
        new_raw_levels: dict[RiskDimension, RiskLevel],
        previous_state: WellbeingState,
        signals_recent_72h: list[WellbeingSignal] | None = None,
    ) -> dict[RiskDimension, RiskLevel]:
        t = self._thresholds
        result: dict[RiskDimension, RiskLevel] = {}
        has_acute = self._has_acute_event(signals_recent_72h or [])

        for dim, new_raw in new_raw_levels.items():
            old = self._get_previous_level(previous_state, dim)
            if new_raw > old:
                result[dim] = new_raw
            elif new_raw < old:
                if self._should_demote(previous_state, dim, old, new_raw, has_acute):
                    result[dim] = new_raw
                else:
                    result[dim] = old
            else:
                result[dim] = old

        return result

    def update_demotion_counters(
        self, new_raw_levels: dict[RiskDimension, RiskLevel], state: WellbeingState
    ) -> WellbeingState:
        any_below = any(
            new_raw_levels.get(dim, RiskLevel.LOW) < self._get_previous_level(state, dim)
            for dim in RiskDimension
        )
        if any_below:
            state.consecutive_below_high += 1
            state.consecutive_below_critical += 1
        else:
            state.consecutive_below_high = 0
            state.consecutive_below_critical = 0
        return state

    @staticmethod
    def _get_previous_level(state: WellbeingState, dim: RiskDimension) -> RiskLevel:
        mapping = {
            RiskDimension.SUICIDE_RISK: state.suicide_risk,
            RiskDimension.DEPRESSION_SIGNALS: state.depression_signals,
            RiskDimension.DEPENDENCY_RISK: state.dependency_risk,
            RiskDimension.ADDICTION_SIGNALS: state.addiction_signals,
        }
        return mapping.get(dim, RiskLevel.LOW)

    def _should_demote(
        self, state: WellbeingState, dim: RiskDimension,
        old_level: RiskLevel, new_level: RiskLevel, has_acute_72h: bool,
    ) -> bool:
        t = self._thresholds

        if old_level == RiskLevel.HIGH and new_level <= RiskLevel.MEDIUM:
            return state.consecutive_below_high >= t.demotion_high_to_medium_checks
        if old_level == RiskLevel.CRITICAL and new_level <= RiskLevel.HIGH:
            return state.consecutive_below_critical >= t.demotion_critical_to_high_checks
        if new_level == RiskLevel.LOW and has_acute_72h:
            return False
        return True

    @staticmethod
    def _has_acute_event(signals_72h: list[WellbeingSignal]) -> bool:
        for s in signals_72h:
            if s.is_purple or s.interaction_duration_minutes > 240:
                return True
        return False


# ============================================================
# Wellbeing Monitor — 主类
# ============================================================


class WellbeingMonitor:
    """健康监测器主类（§1, §8）。

    Usage:
        monitor = WellbeingMonitor(alert_callback=my_alert_handler)
        monitor.append_signal(signal)
        state, directive, alerts = monitor.recompute("u1", "c1")
    """

    def __init__(
        self,
        thresholds: Thresholds | None = None,
        alert_callback: AlertCallback | None = None,
    ):
        self._thresholds = thresholds or Thresholds()
        self._aggregator = WindowAggregator(self._thresholds)
        self._scorer = RiskScorer(self._thresholds)
        self._hysteresis = HysteresisManager(self._thresholds)
        self._alert_callback = alert_callback

        self._signal_logs: dict[str, list[WellbeingSignal]] = {}
        self._states: dict[str, WellbeingState] = {}
        self._alerts: list[WellbeingAlert] = []
        self._directives: dict[str, WellbeingDirective] = {}

    # -------- 公共 API --------

    def append_signal(self, signal: WellbeingSignal) -> None:
        key = self._user_key(signal.user_id, signal.character_id)
        self._signal_logs.setdefault(key, []).append(signal)
        logger.debug(
            "Wellbeing signal appended user=%s char=%s turn=%s level=%s",
            signal.user_id, signal.character_id, signal.turn_id, signal.safety_level,
        )

    def recompute(
        self, user_id: str, character_id: str, now: datetime | None = None,
    ) -> tuple[WellbeingState, WellbeingDirective, list[WellbeingAlert]]:
        key = self._user_key(user_id, character_id)
        signals = self._signal_logs.get(key, [])
        now = now or datetime.now(timezone.utc)
        previous_state = self._states.get(key)

        # 1. 聚合
        aggregates = self._aggregator.aggregate(signals, now)

        # 2. 原始评分
        raw_levels = self._scorer.score_all(aggregates, previous_state)

        # 3. 滞后
        if previous_state is not None:
            previous_state = self._hysteresis.update_demotion_counters(raw_levels, previous_state)
            cutoff_72h = now - timedelta(hours=72)
            signals_72h = [s for s in signals if s.created_at >= cutoff_72h]
            final_levels = self._hysteresis.apply(raw_levels, previous_state, signals_72h)
        else:
            final_levels = raw_levels

        # 4. 构建状态
        state = self._build_state(user_id, aggregates, final_levels, previous_state, now)

        # 5. 干预生命周期
        state, intervention_alerts = self._manage_interventions(state, previous_state, signals, now)

        # 6. 动作阶梯
        dominant_tier, extra = ActionLadder.resolve(final_levels)

        # 7. 指令
        directive = self._build_directive(user_id, character_id, dominant_tier, extra, state, now)

        # 8. 等级变化告警
        level_change_alerts = self._detect_level_changes(final_levels, previous_state, user_id)
        all_alerts = level_change_alerts + intervention_alerts

        # 9. 持久化
        self._states[key] = state
        self._directives[key] = directive
        self._alerts.extend(all_alerts)

        for alert in all_alerts:
            self._emit_alert(alert)

        return state, directive, all_alerts

    def get_state(self, user_id: str, character_id: str) -> WellbeingState | None:
        return self._states.get(self._user_key(user_id, character_id))

    def get_directive(self, user_id: str, character_id: str) -> WellbeingDirective | None:
        return self._directives.get(self._user_key(user_id, character_id))

    def get_alerts(self, user_id: str | None = None) -> list[WellbeingAlert]:
        if user_id is None:
            return list(self._alerts)
        return [a for a in self._alerts if a.user_id == user_id]

    # -------- 干预生命周期 (§6.4) --------

    def _manage_interventions(
        self, state: WellbeingState, previous_state: WellbeingState | None,
        signals: list[WellbeingSignal], now: datetime,
    ) -> tuple[WellbeingState, list[WellbeingAlert]]:
        alerts: list[WellbeingAlert] = []
        t = self._thresholds

        # --- suicide_protocol ---
        if state.suicide_risk >= RiskLevel.HIGH:
            if previous_state is None or not previous_state.suicide_protocol_active:
                state.suicide_protocol_active = True
                state.care_path_remaining_turns = t.care_path_default_turns
                alerts.append(WellbeingAlert(
                    user_id=state.user_id, alert_type="intervention_started",
                    dimension=RiskDimension.SUICIDE_RISK, new_level=state.suicide_risk,
                    rule_fired="suicide_protocol_activated",
                ))
            else:
                if state.care_path_remaining_turns > 0:
                    state.care_path_remaining_turns -= 1
        else:
            prev_active = previous_state is not None and previous_state.suicide_protocol_active
            if prev_active:
                if self._can_exit_care_path(state, previous_state, signals, t):
                    state.suicide_protocol_active = False
                    state.care_path_remaining_turns = 0
                    alerts.append(WellbeingAlert(
                        user_id=state.user_id, alert_type="intervention_ended",
                        dimension=RiskDimension.SUICIDE_RISK,
                        rule_fired="suicide_protocol_exit_conditions_met",
                    ))
                elif state.care_path_remaining_turns <= 0:
                    state.care_path_remaining_turns = t.care_path_default_turns

        # --- dependency_throttle ---
        if state.dependency_risk >= RiskLevel.HIGH:
            prev_active_dep = previous_state is not None and previous_state.dependency_throttle_active
            if not prev_active_dep:
                state.dependency_throttle_active = True
                alerts.append(WellbeingAlert(
                    user_id=state.user_id, alert_type="intervention_started",
                    dimension=RiskDimension.DEPENDENCY_RISK, new_level=state.dependency_risk,
                    rule_fired="dependency_throttle_activated",
                ))
        elif previous_state is not None and previous_state.dependency_throttle_active:
            if self._can_exit_dependency_throttle(state):
                state.dependency_throttle_active = False
                alerts.append(WellbeingAlert(
                    user_id=state.user_id, alert_type="intervention_ended",
                    dimension=RiskDimension.DEPENDENCY_RISK,
                    rule_fired="dependency_throttle_exit_conditions_met",
                ))

        # --- addiction_intervention ---
        if state.addiction_signals >= RiskLevel.HIGH:
            prev_active_add = previous_state is not None and previous_state.addiction_intervention_active
            if not prev_active_add:
                state.addiction_intervention_active = True
                alerts.append(WellbeingAlert(
                    user_id=state.user_id, alert_type="intervention_started",
                    dimension=RiskDimension.ADDICTION_SIGNALS, new_level=state.addiction_signals,
                    rule_fired="addiction_intervention_activated",
                ))
        elif previous_state is not None and previous_state.addiction_intervention_active:
            if self._can_exit_addiction_intervention(state):
                state.addiction_intervention_active = False
                alerts.append(WellbeingAlert(
                    user_id=state.user_id, alert_type="intervention_ended",
                    dimension=RiskDimension.ADDICTION_SIGNALS,
                    rule_fired="addiction_intervention_exit_conditions_met",
                ))

        return state, alerts

    @staticmethod
    def _can_exit_care_path(
        state: WellbeingState, previous_state: WellbeingState,
        signals: list[WellbeingSignal], t: Thresholds,
    ) -> bool:
        if state.care_path_remaining_turns > 0:
            return False
        now = datetime.now(timezone.utc)
        cutoff_7d = now - timedelta(days=7)
        if any(s.is_purple and s.created_at >= cutoff_7d for s in signals):
            return False
        if state.negative_sentiment_ratio_7d >= state.negative_sentiment_baseline_30d:
            return False
        return True

    @staticmethod
    def _can_exit_dependency_throttle(state: WellbeingState) -> bool:
        return state.avg_daily_usage_minutes_7d < 90.0 and state.irl_contact_mentions_7d >= 1

    @staticmethod
    def _can_exit_addiction_intervention(state: WellbeingState) -> bool:
        return state.peak_session_minutes_7d < 240.0 and state.consecutive_late_night_days == 0

    # -------- 内部 helpers --------

    @staticmethod
    def _user_key(user_id: str, character_id: str) -> str:
        return f"{user_id}:{character_id}"

    def _build_state(
        self, user_id: str, aggregates: dict[str, Any],
        final_levels: dict[RiskDimension, RiskLevel],
        previous_state: WellbeingState | None, now: datetime,
    ) -> WellbeingState:
        base = previous_state if previous_state is not None else WellbeingState(user_id=user_id)
        agg_fields = {k: aggregates[k] for k in (
            "purple_hit_count_7d", "purple_hit_count_30d",
            "dark_language_density_7d", "dark_language_density_30d",
            "negative_sentiment_ratio_7d", "negative_sentiment_ratio_30d",
            "consecutive_emotional_distress_days", "topic_breadth_7d",
            "irl_contact_mentions_7d", "irl_contact_mentions_30d",
            "late_night_usage_ratio_7d", "late_night_usage_ratio_30d",
            "avg_daily_usage_minutes_7d", "sessions_per_day_7d",
            "emotional_reliance_ratio_7d", "consecutive_daily_usage_streak",
            "peak_session_minutes_7d", "consecutive_late_night_days",
            "daily_usage_variance_7d", "negative_sentiment_baseline_30d",
            "total_turns", "total_days",
        )}
        state = WellbeingState(
            user_id=user_id,
            suicide_risk=final_levels.get(RiskDimension.SUICIDE_RISK, RiskLevel.LOW),
            depression_signals=final_levels.get(RiskDimension.DEPRESSION_SIGNALS, RiskLevel.LOW),
            dependency_risk=final_levels.get(RiskDimension.DEPENDENCY_RISK, RiskLevel.LOW),
            addiction_signals=final_levels.get(RiskDimension.ADDICTION_SIGNALS, RiskLevel.LOW),
            suicide_protocol_active=base.suicide_protocol_active,
            care_path_remaining_turns=base.care_path_remaining_turns,
            dependency_throttle_active=base.dependency_throttle_active,
            addiction_intervention_active=base.addiction_intervention_active,
            consecutive_below_high=base.consecutive_below_high,
            consecutive_below_critical=base.consecutive_below_critical,
            updated_at=now,
            last_recompute_at=now,
            **agg_fields,
        )
        return state

    def _build_directive(
        self, user_id: str, character_id: str, dominant_tier: ActionTier,
        extra: dict[str, Any], state: WellbeingState, now: datetime,
    ) -> WellbeingDirective:
        directive = WellbeingDirective(
            user_id=user_id, character_id=character_id,
            active_tier=dominant_tier,
            soul_flavored_lines_allowed=extra.get("soul_flavored_lines_allowed", []),
            proactive_throttle=extra.get("proactive_throttle", 1.0),
            care_path_active=state.suicide_protocol_active,
            care_path_remaining_turns=state.care_path_remaining_turns,
            set_at=now,
            expires_at=now + timedelta(hours=24) if dominant_tier >= ActionTier.T1 else None,
        )
        if dominant_tier >= ActionTier.T4:
            directive.alert_payload = {
                "user_id": user_id, "character_id": character_id,
                "tier": dominant_tier.value, "suicide_risk": state.suicide_risk.value,
                "purple_hit_count_7d": state.purple_hit_count_7d,
                "care_path_remaining_turns": state.care_path_remaining_turns,
            }
        return directive

    def _detect_level_changes(
        self, final_levels: dict[RiskDimension, RiskLevel],
        previous_state: WellbeingState | None, user_id: str,
    ) -> list[WellbeingAlert]:
        if previous_state is None:
            return []

        prev_levels = {
            RiskDimension.SUICIDE_RISK: previous_state.suicide_risk,
            RiskDimension.DEPRESSION_SIGNALS: previous_state.depression_signals,
            RiskDimension.DEPENDENCY_RISK: previous_state.dependency_risk,
            RiskDimension.ADDICTION_SIGNALS: previous_state.addiction_signals,
        }
        alerts: list[WellbeingAlert] = []
        for dim, new_level in final_levels.items():
            old_level = prev_levels.get(dim, RiskLevel.LOW)
            if new_level != old_level:
                prev_tier = ActionLadder._LADDER.get((dim, old_level), ActionTier.T0)
                new_tier_val = ActionLadder._LADDER.get((dim, new_level), ActionTier.T0)
                alerts.append(WellbeingAlert(
                    user_id=user_id, alert_type="risk_level_change",
                    dimension=dim, previous_level=old_level, new_level=new_level,
                    previous_tier=prev_tier, new_tier=new_tier_val,
                    rule_fired=f"{dim.value}:{old_level.value}→{new_level.value}",
                ))
        return alerts

    def _emit_alert(self, alert: WellbeingAlert) -> None:
        if self._alert_callback is not None:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self._alert_callback):
                    logger.info(
                        "Alert (async cb pending) type=%s user=%s dim=%s %s→%s",
                        alert.alert_type, alert.user_id,
                        alert.dimension.value if alert.dimension else "N/A",
                        alert.previous_level.value if alert.previous_level else "N/A",
                        alert.new_level.value if alert.new_level else "N/A",
                    )
                else:
                    self._alert_callback(alert)  # type: ignore[call-arg]
            except Exception:
                logger.exception("Alert callback failed user=%s", alert.user_id)
        else:
            logger.info(
                "Alert type=%s user=%s dim=%s %s→%s tier=%s→%s",
                alert.alert_type, alert.user_id,
                alert.dimension.value if alert.dimension else "N/A",
                alert.previous_level.value if alert.previous_level else "N/A",
                alert.new_level.value if alert.new_level else "N/A",
                alert.previous_tier.name if alert.previous_tier else "N/A",
                alert.new_tier.name if alert.new_tier else "N/A",
            )
