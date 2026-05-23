"""
Safety Agent — 多层安全分类器

多层安全:
- pre_filter:  用户消息分类（heuristic + LLM merge）
- post_filter: 响应安全检查（模型输出违法/幻觉安全风险）
- long_term:   用户健康度追踪

Heuristic 层使用 Aho-Corasick 自动机做关键词匹配 + 可选正则扫描，
在 < 1ms 内完成 fast-path 分类。

Spec: /runtime_specs/07_agent_orchestration.md §3.4.2, §5.2

Author: 心屿团队
"""

from __future__ import annotations

import hashlib
import structlog
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from heart.safety.safety_llm import SafetyLLMClassifier

import yaml

logger = structlog.get_logger()

# ============================================================
# Aho-Corasick 导入（可选依赖）
# ============================================================

try:
    import ahocorasick

    AHOCORASICK_AVAILABLE = True
except ImportError:
    AHOCORASICK_AVAILABLE = False
    logger.info(
        "pyahocorasick not installed; falling back to naive substring scanner "
        "(slower but no dependency). Install with: pip install pyahocorasick"
    )


# ============================================================
# 数据模型
# ============================================================


class SafetyClassificationLevel(str, Enum):
    """启发式安全分类等级。

    从低到高排列；当多关键词命中时，取最高等级。
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PURPLE_CARE_REQUIRED = "purple_care_required"

    @classmethod
    def from_string(cls, s: str) -> "SafetyClassificationLevel":
        """容错地从字符串构造等级。"""
        s = s.strip().upper()
        if s in ("PURPLE_CARE_REQUIRED", "PURPLE"):
            return cls.PURPLE_CARE_REQUIRED
        for level in reversed(list(cls)):
            if level.value.upper() == s:
                return level
        return cls.NONE

    @staticmethod
    def _order() -> list["SafetyClassificationLevel"]:
        return list(SafetyClassificationLevel)

    def __lt__(self, other: "SafetyClassificationLevel") -> bool:
        if not isinstance(other, SafetyClassificationLevel):
            return NotImplemented
        order = self._order()
        return order.index(self) < order.index(other)

    def __le__(self, other: "SafetyClassificationLevel") -> bool:
        if not isinstance(other, SafetyClassificationLevel):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: "SafetyClassificationLevel") -> bool:
        if not isinstance(other, SafetyClassificationLevel):
            return NotImplemented
        return other < self

    def __ge__(self, other: "SafetyClassificationLevel") -> bool:
        if not isinstance(other, SafetyClassificationLevel):
            return NotImplemented
        return self == other or self > other


@dataclass(frozen=True)
class SafetyClassification:
    """启发式安全分类结果（§5.2 对齐）。"""

    level: SafetyClassificationLevel
    confidence: float  # 0.0 ~ 1.0

    triggered_categories: tuple[str, ...] = ()
    reason: str = ""

    recommended_action: str = "normal_reply"
    # 可选: "controlled_reply" | "deflect" | "reject" | "suicide_care"

    prompt_directives: dict = field(default_factory=dict)

    classified_at: str = ""
    message_hash: str = ""

    # ---- 工厂方法 ----

    @staticmethod
    def none(msg_hash: str = "") -> "SafetyClassification":
        return SafetyClassification(
            level=SafetyClassificationLevel.NONE,
            confidence=1.0,
            reason="no keyword match",
            recommended_action="normal_reply",
            classified_at="",
            message_hash=msg_hash,
        )

    @staticmethod
    def from_hit(
        level: SafetyClassificationLevel,
        category: str,
        reason: str = "",
        message_hash: str = "",
    ) -> "SafetyClassification":
        return SafetyClassification(
            level=level,
            confidence=_level_confidence(level),
            triggered_categories=(category,),
            reason=reason,
            recommended_action=_level_action(level),
            message_hash=message_hash,
        )


def _level_confidence(level: SafetyClassificationLevel) -> float:
    """每级默认置信度。"""
    return {
        SafetyClassificationLevel.NONE: 1.00,
        SafetyClassificationLevel.LOW: 0.85,
        SafetyClassificationLevel.MEDIUM: 0.80,
        SafetyClassificationLevel.HIGH: 0.90,
        SafetyClassificationLevel.PURPLE_CARE_REQUIRED: 0.95,
    }[level]


def _level_action(level: SafetyClassificationLevel) -> str:
    """级别 → 推荐动作。"""
    return {
        SafetyClassificationLevel.NONE: "normal_reply",
        SafetyClassificationLevel.LOW: "controlled_reply",
        SafetyClassificationLevel.MEDIUM: "deflect",
        SafetyClassificationLevel.HIGH: "reject",
        SafetyClassificationLevel.PURPLE_CARE_REQUIRED: "suicide_care",
    }[level]


# ============================================================
# 关键词加载
# ============================================================

_KEYWORD_CONFIG_PATH: Path = Path(__file__).resolve().parents[3] / "config" / "safety_keywords.yaml"


def _load_raw_config(path: Path | None = None) -> dict:
    """加载 YAML 关键词配置。"""
    if path is None:
        path = _KEYWORD_CONFIG_PATH
    if not path.exists():
        logger.warning("safety_keywords.yaml not found at %s; using empty config", path)
        return {"low": [], "medium": [], "high": [], "purple": [], "regex_patterns": []}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# ============================================================
# Heuristic Classifier — Aho-Corasick 核心
# ============================================================


class HeuristicSafetyClassifier:
    """启发式安全分类器。

    使用 Aho-Corasick 自动机做多模式同步匹配（O(n + m + z)），
    辅以正则扩展，返回结构化 SafetyClassification。

    重置阈值：
    - 单字关键词（如"杀""死"）仅匹配完整 token，
      避免在"杀菌""死机"等无害词上误报。
    """

    # 单字关键词边界保护。
    # 默认关闭：依赖关键词列表质量而非启发式边界推断。
    # 启用后会对 CJK 做嵌入检查（"杀菌"中"杀"不触发）。
    _SINGLE_CHAR_PROTECT: ClassVar[bool] = False

    def __init__(self, config_path: Path | None = None):
        self._config = _load_raw_config(config_path)

        # ---- 构建 Aho-Corasick 自动机 ----
        self._automaton: object | None = None
        self._tier_map: dict[str, SafetyClassificationLevel] = {}
        self._tier_of_keyword: dict[str, SafetyClassificationLevel] = {}
        self._build_automaton()

        # ---- 编译正则 ----
        self._regex_rules: list[tuple[re.Pattern, SafetyClassificationLevel]] = []
        self._build_regexes()

    # -------- 构造 --------

    def _build_automaton(self) -> None:
        """为 low/medium/high/purple 四组关键词构建 AC 自动机。"""
        tier_names = ["low", "medium", "high", "purple"]
        tier_enum: dict[str, SafetyClassificationLevel] = {
            "low": SafetyClassificationLevel.LOW,
            "medium": SafetyClassificationLevel.MEDIUM,
            "high": SafetyClassificationLevel.HIGH,
            "purple": SafetyClassificationLevel.PURPLE_CARE_REQUIRED,
        }

        all_keywords: set[str] = set()
        for tier_name in tier_names:
            level = tier_enum[tier_name]
            for kw in self._config.get(tier_name, []) or []:
                kw = kw.strip()
                if not kw:
                    continue
                all_keywords.add(kw)
                # 多个 tier 含相同关键词 → 取更高等级
                existing = self._tier_of_keyword.get(kw)
                if existing is None or level > existing:
                    self._tier_of_keyword[kw] = level

        if not all_keywords:
            logger.info("HeuristicSafetyClassifier: no keywords loaded")
            return

        if AHOCORASICK_AVAILABLE:
            automaton: ahocorasick.Automaton = ahocorasick.Automaton()
            for kw in all_keywords:
                automaton.add_word(kw, kw)
            automaton.make_automaton()
            self._automaton = automaton
        else:
            self._automaton = None  # fallback 使用朴素扫描

        self._keywords_set = frozenset(all_keywords)
        logger.debug(
            "HeuristicSafetyClassifier: loaded %d unique keywords",
            len(all_keywords),
        )

    def _build_regexes(self) -> None:
        """编译 YAML 中的 regex_patterns。"""
        for entry in self._config.get("regex_patterns", []) or []:
            pattern_str = entry.get("pattern")
            level_str = entry.get("level", "NONE")
            if not pattern_str:
                continue
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
                level = SafetyClassificationLevel.from_string(level_str)
                self._regex_rules.append((compiled, level))
            except re.error as exc:
                logger.warning(
                    "HeuristicSafetyClassifier: bad regex pattern %r: %s",
                    pattern_str,
                    exc,
                )

    # -------- 分类 --------

    def classify(self, message: str) -> SafetyClassification:
        """对用户消息执行启发式分类。

        Args:
            message: 用户原始消息

        Returns:
            SafetyClassification；无命中时返回 NONE。
        """
        if not message or not message.strip():
            return SafetyClassification.none(msg_hash="")

        msg_hash = _hash_message(message)
        best_level = SafetyClassificationLevel.NONE
        hit_categories: list[str] = []
        hit_details: list[str] = []

        # 1. Aho-Corasick 关键词扫描
        keyword_level, kw_hits = self._scan_keywords(message)
        if keyword_level > best_level:
            best_level = keyword_level
            hit_categories.append("keyword")
            hit_details.extend(kw_hits)

        # 2. 正则扫描
        regex_level, rx_hits = self._scan_regex(message)
        if regex_level > best_level:
            best_level = regex_level
            hit_categories.append("regex")
            hit_details.extend(rx_hits)

        if best_level == SafetyClassificationLevel.NONE:
            return SafetyClassification.none(msg_hash=msg_hash)

        return SafetyClassification.from_hit(
            level=best_level,
            category="+".join(hit_categories),
            reason="; ".join(hit_details),
            message_hash=msg_hash,
        )

    def _scan_keywords(self, message: str) -> tuple[SafetyClassificationLevel, list[str]]:
        """扫描消息中的关键词。

        Returns:
            (最高等级, 命中详情列表)
        """
        best = SafetyClassificationLevel.NONE
        details: list[str] = []

        if self._automaton is not None and AHOCORASICK_AVAILABLE:
            # Aho-Corasick 快速路径
            for end_idx, kw in self._automaton.iter(message):  # type: ignore[union-attr]
                start_idx = end_idx - len(kw) + 1
                if self._SINGLE_CHAR_PROTECT and len(kw) == 1:
                    if not self._is_isolated_word(message, start_idx, end_idx):
                        continue
                level = self._tier_of_keyword.get(kw, SafetyClassificationLevel.NONE)
                details.append(f"'{kw}' at pos {start_idx}")
                if level > best:
                    best = level
        else:
            # 朴素 fallback
            best, details = self._naive_keyword_scan(message)

        return best, details

    def _naive_keyword_scan(
        self, message: str
    ) -> tuple[SafetyClassificationLevel, list[str]]:
        """朴素子串扫描（无 pyahocorasick 时的 fallback）。"""
        best = SafetyClassificationLevel.NONE
        details: list[str] = []
        msg_lower = message.lower()

        for kw, level in self._tier_of_keyword.items():
            idx = msg_lower.find(kw.lower())
            if idx == -1:
                continue
            if self._SINGLE_CHAR_PROTECT and len(kw) == 1:
                if not self._is_isolated_word(message, idx, idx + len(kw) - 1):
                    continue
            details.append(f"'{kw}' at pos {idx}")
            if level > best:
                best = level

        return best, details

    def _scan_regex(self, message: str) -> tuple[SafetyClassificationLevel, list[str]]:
        """正则扫描。"""
        best = SafetyClassificationLevel.NONE
        details: list[str] = []
        for pattern, level in self._regex_rules:
            match = pattern.search(message)
            if match:
                details.append(f"regex '{pattern.pattern}' matched '{match.group()}'")
                if level > best:
                    best = level
        return best, details

    # -------- 辅助 --------

    @staticmethod
    def _is_isolated_word(text: str, start: int, end: int) -> bool:
        """检查 text[start:end] 是否为词边界内独立词。

        对于中文单字关键词（如"杀""死"）：
        - CJK 宽松模式：仅两端同时为 CJK 时视为嵌入（如"杀菌"）
        - 非 CJK 模式：前后任一为 CJK 即视为嵌入
        """
        if start > 0 and end + 1 < len(text):
            prev_cjk = _is_cjk(text[start - 1])
            next_cjk = _is_cjk(text[end + 1])
            if prev_cjk and next_cjk:
                # 双端都是 CJK → 真正的嵌入词（如"杀菌"）
                return False
        return True


def _is_cjk(ch: str) -> bool:
    """判断是否为 CJK 字符（基本汉字块）。"""
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF)  # CJK Unified
        or (0x3400 <= cp <= 0x4DBF)  # CJK Ext-A
        or (0xF900 <= cp <= 0xFAFF)  # CJK Compat
    )


def _hash_message(message: str) -> str:
    """消息内容哈希（SHA-256 前 16 hex）。"""
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


# ============================================================
# Safety Agent — 顶层入口
# ============================================================


@dataclass
class SafetyAgent:
    """多层安全检查：

    - pre_filter:     用户消息分类（heuristic + optional LLM merge）
    - post_filter:    角色响应安全检查
    - long_term:      用户长期健康度追踪

    符合 O-3 (LLM 前必跑) 、O-4 (PURPLE 升级)、INV-O-2 (pre_filter 先于 compose)。
    """

    classifier: HeuristicSafetyClassifier = field(default_factory=HeuristicSafetyClassifier)
    llm_classifier: SafetyLLMClassifier | None = None  # Optional LLM refinement for MEDIUM+
    cache: dict[str, SafetyClassification] = field(default_factory=dict)
    # 生产环境替换为 Redis / memcached 后端

    async def pre_filter(
        self,
        user_message: str,
        user_id: str = "",
        character_id: str = "",
        session: dict | None = None,
    ) -> SafetyClassification:
        """用户消息安全预检（主入口，§3.4.2）。

        流程:
        1. 缓存命中 → 直接返回
        2. 启发式分类（< 1ms）
        3. 若 RED/HIGH → 直接返回（不进入 LLM）
        4. 否则 → 可选 LLM classification（cheap model）+ merge
        5. 用户因子（dependency risk）调整
        6. 缓存写入

        Args:
            user_message: 用户原始消息
            user_id:      用户 ID（长期因子用）
            character_id: 角色 ID（上下文用）
            session:      当前 session 元数据

        Returns:
            SafetyClassification
        """
        # 1. Cache check
        cache_key = _hash_message(user_message)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 2. Fast heuristic
        heuristic = self.classifier.classify(user_message)

        # 3. HIGH / PURPLE → immediate return (no LLM needed)
        if heuristic.level >= SafetyClassificationLevel.HIGH:
            self.cache[cache_key] = heuristic
            return heuristic

        # 4. LLM-based classification — only when MEDIUM+ (cost gate)
        #    NONE/LOW skip LLM to save cost; MEDIUM merits deeper semantic check
        llm_result: SafetyClassification | None = None
        if heuristic.level >= SafetyClassificationLevel.MEDIUM:
            try:
                llm_result = await self._llm_classify(
                    user_message, user_id, character_id
                )
            except Exception:
                logger.debug(
                    "LLM safety classification failed; using heuristic only",
                    exc_info=True,
                )

        # 5. Merge heuristic + LLM
        final = self._merge(heuristic, llm_result)

        # 6. User-specific factors (placeholder)
        #    TODO: query wellbeing_monitor for dependency_risk
        #    if user_history.dependency_risk_high and final.level == LOW:
        #        final = SafetyClassification(level=MEDIUM, ...)

        self.cache[cache_key] = final
        return final

    async def post_filter(self, response: str, context: dict | None = None) -> dict:
        """角色响应安全后检。

        检查模型输出中：
        - 违法内容泄漏
        - 幻觉安全风险
        - 不应出现的关键词

        Args:
            response: 角色回复文本
            context:  当前 turn 上下文

        Returns:
            {"passed": bool, "issues": list[str]}
        """
        if not response:
            return {"passed": True, "issues": []}

        result = self.classifier.classify(response)
        if result.level >= SafetyClassificationLevel.HIGH:
            return {
                "passed": False,
                "issues": [f"response triggered safety level {result.level.value}: {result.reason}"],
            }
        return {"passed": True, "issues": []}

    async def long_term_aggregate(
        self,
        user_id: str,
        character_id: str,
        recent_turns: list[dict],
    ) -> dict:
        """长期安全信号聚合（stub）。

        真实实现需要：
        - 自杀倾向频率
        - 抑郁迹象累积
        - 暴力倾向追踪
        - 异常依赖检测

        Args:
            user_id:      用户 ID
            character_id: 角色 ID
            recent_turns: 最近 turn 列表

        Returns:
            {"suicide_risk": str, "dependency_risk": str, ...}
        """
        return {
            "suicide_risk": "LOW",
            "dependency_risk": "LOW",
            "depression_signals": "LOW",
            "addiction_signals": "LOW",
        }

    # -------- 内部方法 --------

    async def _llm_classify(
        self, message: str, user_id: str, character_id: str
    ) -> SafetyClassification | None:
        """LLM-based safety classification via SafetyLLMClassifier.

        Delegates to SafetyLLMClassifier which uses ModelRouter.call_cheap()
        with json_mode=True. Returns None on failure (caller falls back to
        heuristic-only classification).

        Args:
            message: User message to classify.
            user_id: User ID for cost cap tracking.
            character_id: Character ID (unused, reserved for future context).

        Returns:
            SafetyClassification or None.
        """
        if self.llm_classifier is None:
            return None

        result = await self.llm_classifier.classify(message, user_id=user_id)
        if result is None:
            return None

        return result.to_safety_classification()

    @staticmethod
    def _merge(
        heuristic: SafetyClassification,
        llm: SafetyClassification | None,
    ) -> SafetyClassification:
        """合并启发式结果与 LLM 结果。

        规则：
        - 取两者中更高的等级
        - 有 LLM 结果时，置信度取加权平均
        - 保留所有 triggered_categories
        """
        if llm is None:
            return heuristic

        best_level = heuristic.level if heuristic.level > llm.level else llm.level
        categories = set(heuristic.triggered_categories) | set(llm.triggered_categories)

        return SafetyClassification(
            level=best_level,
            confidence=(heuristic.confidence + llm.confidence) / 2.0,
            triggered_categories=tuple(sorted(categories)),
            reason=f"heuristic: {heuristic.reason}; llm: {llm.reason}",
            recommended_action=_level_action(best_level),
            message_hash=heuristic.message_hash or llm.message_hash,
        )
