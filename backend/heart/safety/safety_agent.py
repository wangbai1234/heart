"""
SafetyAgent — SS07 Orchestration safety classifier per docs/design/safety_overhaul.md.

Three-layer classification:
  Layer 1 (heuristic): Multi-language regex lexicon — instant, no IO.
  Layer 2 (LLM): DeepSeek cheap-tier classification with 500ms timeout fallback.
  Layer 3 (Wellbeing): Sliding-window accumulation for progressive escalation.

PURPLE care path: blocks user message from reaching Soul composition.
Vulnerability detection and severity routing.

Author: Heart Platform
"""

from __future__ import annotations

import asyncio
import json
import re
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
import yaml

from heart.infra.invariants import invariant

import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip

logger = structlog.get_logger(__name__)

# ── Config paths ────────────────────────────────────────────────────

_LEXICON_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "safety" / "crisis_lexicon"
)
_CARE_PATH_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "config"
    / "safety"
    / "care_path_responses"
)


# ── Data types ───────────────────────────────────────────────────────


class SeverityLevel(str, Enum):
    """Message severity classification."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    PURPLE = "PURPLE"

    @property
    def ordinal(self) -> int:
        _order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3, "PURPLE": 4}
        return _order[self.value]


@dataclass
class ClassificationResult:
    """Result of safety classification for one turn."""

    severity: SeverityLevel
    reason: str
    triggered_rules: list[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    layer: str = "heuristic"


# ── Lexicon data ─────────────────────────────────────────────────────


@dataclass
class CompiledPattern:
    regex: re.Pattern
    severity_default: str
    category: str
    pattern_index: int
    exemptions: List[Tuple[re.Pattern, str]] = field(default_factory=list)


@dataclass
class Lexicon:
    language: str
    version: str
    patterns: List[CompiledPattern] = field(default_factory=list)


# ── Lexicon Loader ───────────────────────────────────────────────────


class LexiconLoader:
    """Load and compile multi-language regex lexicon from YAML files."""

    def __init__(self, lexicon_dir: Optional[Path] = None, care_path_dir: Optional[Path] = None):
        self._lexicon_dir = lexicon_dir or _LEXICON_DIR
        self._care_path_dir = care_path_dir or _CARE_PATH_DIR
        self._lexicons: Dict[str, Lexicon] = {}
        self._care_paths: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def load_all(self) -> None:
        """Load all lexicon files and care-path templates at startup."""
        self._load_lexicons()
        self._load_care_paths()
        self._loaded = True
        logger.info(
            "lexicon_loader_initialized",
            languages=list(self._lexicons.keys()),
            care_path_locales=list(self._care_paths.keys()),
        )

    def _load_lexicons(self) -> None:
        if not self._lexicon_dir.exists():
            logger.warning("lexicon_dir_not_found", path=str(self._lexicon_dir))
            return

        for yaml_file in sorted(self._lexicon_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r") as f:
                    raw = yaml.safe_load(f)
                lang = raw.get("language", yaml_file.stem)
                compiled = Lexicon(language=lang, version=raw.get("version", "0.0.0"))

                for cat_name, cat_data in raw.get("categories", {}).items():
                    sev_default = cat_data.get("severity_default", "GREEN")
                    for idx, pat_data in enumerate(cat_data.get("patterns", [])):
                        try:
                            regex = re.compile(pat_data["regex"], re.IGNORECASE | re.UNICODE)
                        except re.error as e:
                            logger.error(
                                "lexicon_regex_compile_failed",
                                file=str(yaml_file),
                                category=cat_name,
                                pattern_index=idx,
                                error=str(e),
                            )
                            continue
                        exemptions = []
                        for exc in pat_data.get("false_positive_exemptions", []):
                            try:
                                exc_regex = re.compile(
                                    exc["context_regex"], re.IGNORECASE | re.UNICODE
                                )
                                exemptions.append(
                                    (exc_regex, exc.get("action", "downgrade_to_green"))
                                )
                            except re.error as e:
                                logger.error(
                                    "lexicon_exemption_regex_compile_failed",
                                    file=str(yaml_file),
                                    error=str(e),
                                )
                        compiled.patterns.append(
                            CompiledPattern(
                                regex=regex,
                                severity_default=sev_default,
                                category=cat_name,
                                pattern_index=idx,
                                exemptions=exemptions,
                            )
                        )

                self._lexicons[lang] = compiled
                logger.info(
                    "lexicon_loaded",
                    language=lang,
                    version=compiled.version,
                    pattern_count=len(compiled.patterns),
                )
            except Exception as e:
                logger.error("lexicon_load_failed", file=str(yaml_file), error=str(e))

    def _load_care_paths(self) -> None:
        if not self._care_path_dir.exists():
            logger.warning("care_path_dir_not_found", path=str(self._care_path_dir))
            return

        for yaml_file in sorted(self._care_path_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r") as f:
                    raw = yaml.safe_load(f)
                locale = raw.get("locale", yaml_file.stem)
                self._care_paths[locale] = raw
                logger.info(
                    "care_path_loaded",
                    locale=locale,
                    version=raw.get("version", "0.0.0"),
                    jurisdictions=list(raw.get("jurisdictions", {}).keys()),
                )
            except Exception as e:
                logger.error("care_path_load_failed", file=str(yaml_file), error=str(e))

    def get_lexicon(self, language: str) -> Optional[Lexicon]:
        return self._lexicons.get(language)

    def get_all_lexicons(self) -> Dict[str, Lexicon]:
        return self._lexicons

    def get_care_path(self, locale: str) -> Optional[Dict[str, Any]]:
        return self._care_paths.get(locale)

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# ── Locale Detection ─────────────────────────────────────────────────


def detect_locale(message: str, accept_language: Optional[str] = None) -> str:
    """Detect locale from message text using Unicode range heuristics.

    Returns one of: 'zh', 'ja', 'en'.
    Falls back to accept-language header if message is ambiguous.
    """
    cjk = 0
    hiragana = 0
    katakana = 0
    latin = 0

    for ch in message:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF:
            cjk += 1
        elif 0x3040 <= cp <= 0x309F:
            hiragana += 1
        elif 0x30A0 <= cp <= 0x30FF:
            katakana += 1
        elif ch.isalpha() and cp < 256:
            latin += 1

    jp_kana = hiragana + katakana

    if jp_kana > 0:
        return "ja"
    if cjk > 0:
        return "zh"

    if accept_language:
        al = accept_language.lower()
        if "ja" in al:
            return "ja"
        if "zh" in al:
            return "zh"
    return "en"


# ── Wellbeing Accumulator (Layer 3) ──────────────────────────────────


@dataclass
class _WellbeingState:
    user_id: UUID
    window_turns: int = 20
    despair_signals: deque = field(default_factory=lambda: deque(maxlen=20))
    loneliness_signals: deque = field(default_factory=lambda: deque(maxlen=20))
    sleep_signals: deque = field(default_factory=lambda: deque(maxlen=20))
    last_purple_at: Optional[float] = None


class WellbeingAccumulator:
    """Sliding-window accumulator for per-user wellbeing signals (Layer 3).

    Tracks despair, loneliness, and sleep disturbance signals across turns.
    Escalates severity when cumulative thresholds are crossed.
    """

    def __init__(self):
        self._states: Dict[str, _WellbeingState] = {}

    def get_state(self, user_id: UUID) -> _WellbeingState:
        sid = str(user_id)
        if sid not in self._states:
            self._states[sid] = _WellbeingState(user_id=user_id)
        return self._states[sid]

    def update(self, user_id: UUID, signals: Dict[str, float]) -> Dict[str, Any]:
        """Record turn signals and check escalation thresholds.

        Args:
            user_id: User UUID.
            signals: Dict with optional keys:
                despair (0-1), loneliness (0-1), sleep_disturbance (0-1),
                category, severity.

        Returns:
            Dict with 'escalated' bool and 'escalated_severity' if true.
        """
        state = self.get_state(user_id)
        now = (
            asyncio.get_event_loop().time()
            if asyncio.get_event_loop().is_running()
            else __import__("time").time()
        )

        state.despair_signals.append(signals.get("despair", 0.0))
        state.loneliness_signals.append(signals.get("loneliness", 0.0))
        state.sleep_signals.append(signals.get("sleep_disturbance", 0.0))

        if signals.get("severity") == "PURPLE":
            state.last_purple_at = now

        result: Dict[str, Any] = {"escalated": False}

        despair_count = sum(1 for s in state.despair_signals if s > 0.5)
        loneliness_count = sum(1 for s in state.loneliness_signals if s > 0.5)
        sleep_count = sum(1 for s in state.sleep_signals if s > 0.5)

        if despair_count >= 8:
            result["escalated"] = True
            result["escalated_severity"] = "PURPLE"
            result["escalation_reason"] = (
                f"Despair signals in {despair_count}/{len(state.despair_signals)} recent turns"
            )
            logger.warning(
                "wellbeing_escalation_despair", user_id=str(user_id), despair_count=despair_count
            )

        if loneliness_count >= 12 and sleep_count >= 5:
            if not result.get("escalated"):
                result["escalated"] = True
                result["escalated_severity"] = "YELLOW"
                result["escalation_reason"] = (
                    f"Loneliness {loneliness_count}/20 AND sleep {sleep_count}/20"
                )
            logger.warning("wellbeing_escalation_loneliness_sleep", user_id=str(user_id))

        if (
            state.last_purple_at is not None
            and (now - state.last_purple_at) < (7 * 86400)
            and signals.get("severity_ordinal", 0) >= SeverityLevel.ORANGE.ordinal
        ):
            result["escalated"] = True
            result["escalated_severity"] = "PURPLE"
            result["escalation_reason"] = "Within 7 days of previous PURPLE event"
            logger.warning("wellbeing_escalation_recent_purple", user_id=str(user_id))

        return result


# ── Safety Agent ─────────────────────────────────────────────────────


@dataclass
class _Layer1Hit:
    pattern: CompiledPattern
    match_text: str
    exempted: bool = False
    final_severity: str = ""


class SafetyAgent:
    """Safety classifier invoked at the orchestrator boundary per turn.

    INV-O-2: Message severity must not be downgraded after an upgrade.
    INV-O-3: PURPLE-level message never reaches Soul composition.

    Three-layer classification per docs/design/safety_overhaul.md:
      Layer 1: Multi-language regex lexicon (instant, no IO).
      Layer 2: LLM-based classification with 500ms timeout fallback.
      Layer 3: Wellbeing accumulator for progressive escalation.
    """

    def __init__(self, lexicon_dir: Optional[Path] = None, care_path_dir: Optional[Path] = None):
        self._loader = LexiconLoader(lexicon_dir=lexicon_dir, care_path_dir=care_path_dir)
        self._loader.load_all()
        self._wellbeing = WellbeingAccumulator()
        self._last_classification: Dict[tuple, ClassificationResult] = {}

    @property
    def lexicon_loader(self) -> LexiconLoader:
        return self._loader

    @property
    def wellbeing(self) -> WellbeingAccumulator:
        return self._wellbeing

    @invariant("inv-o-3.purple-blocked-from-soul")
    @invariant("inv-o-2.message-severity-cap")
    async def classify(
        self,
        message: str,
        *,
        locale: Optional[str] = None,
        user_id: UUID,
        character_id: str,
        turn_id: Optional[UUID] = None,
        model_router: Any = None,
        accept_language: Optional[str] = None,
    ) -> ClassificationResult:
        """Classify a user message for safety severity.

        Called at the orchestrator boundary per §3.9 of spec 07.

        Args:
            message: Raw user message text.
            locale: Locale hint ('zh', 'ja', 'en'). Auto-detected if None.
            user_id: User UUID.
            character_id: Character identifier.
            turn_id: Current turn UUID (optional).
            model_router: ModelRouter instance for Layer 2 LLM (optional).
            accept_language: Accept-Language header for locale fallback.

        Returns:
            ClassificationResult with severity level, reason, and metadata.
        """
        if locale is None:
            locale = detect_locale(message, accept_language)

        result = await self._do_classify(
            message, locale, user_id, character_id, turn_id, model_router
        )
        key = (str(user_id), character_id)
        self._last_classification[key] = result
        return result

    async def _do_classify(
        self,
        message: str,
        locale: str,
        user_id: UUID,
        character_id: str,
        turn_id: Optional[UUID],
        model_router: Any,
    ) -> ClassificationResult:
        # ── Layer 1: Heuristic regex matching ──────────────────────
        l1_result = self._heuristic_layer(message, locale)
        if l1_result.severity == SeverityLevel.PURPLE:
            return l1_result

        if l1_result.severity == SeverityLevel.RED:
            return l1_result

        # ── Layer 2: LLM classification (conditional) ──────────────
        should_call_llm = self._should_call_layer2(l1_result, message)
        l2_result = l1_result
        if should_call_llm and model_router is not None:
            l2_result = await self._llm_layer(message, l1_result, model_router)
            if l2_result.severity == SeverityLevel.PURPLE:
                l2_result.layer = "llm"
                return l2_result

        # ── Layer 3: Wellbeing accumulation ────────────────────────
        effective = l2_result if should_call_llm else l1_result
        signals = self._extract_wellbeing_signals(effective, message)
        escalation = self._wellbeing.update(user_id, signals)

        if escalation.get("escalated"):
            escalated_sev = escalation.get("escalated_severity", "YELLOW")
            if SeverityLevel(escalated_sev).ordinal > effective.severity.ordinal:
                escalation_reason = escalation.get("escalation_reason", "threshold crossed")
                result = ClassificationResult(
                    severity=SeverityLevel(escalated_sev),
                    reason=f"Layer 3 escalation: {escalation_reason}",
                    triggered_rules=effective.triggered_rules + ["wellbeing_escalation"],
                    confidence=effective.confidence,
                    metadata={**effective.metadata, "layer3_escalation": escalation},
                    layer="accumulator",
                )
                return result

        effective.layer = "heuristic"
        return effective

    def _heuristic_layer(self, message: str, locale: str) -> ClassificationResult:
        """Layer 1: Multi-language regex matching without IO."""
        hits: List[_Layer1Hit] = []

        lexicons_to_check = [self._loader.get_lexicon(locale)]
        if locale in ("zh", "ja"):
            other = "ja" if locale == "zh" else "zh"
            other_lex = self._loader.get_lexicon(other)
            if other_lex:
                lexicons_to_check.append(other_lex)
        en_lex = self._loader.get_lexicon("en")
        if en_lex and en_lex not in lexicons_to_check:
            lexicons_to_check.append(en_lex)

        for lexicon in lexicons_to_check:
            if lexicon is None:
                continue
            for pat in lexicon.patterns:
                for m in pat.regex.finditer(message):
                    match_text = m.group(0)
                    exempted = False
                    for exc_regex, _action in pat.exemptions:
                        if exc_regex.search(message):
                            exempted = True
                            break
                    hit = _Layer1Hit(
                        pattern=pat,
                        match_text=match_text,
                        exempted=exempted,
                        final_severity="GREEN" if exempted else pat.severity_default,
                    )
                    hits.append(hit)

        if not hits:
            return ClassificationResult(
                severity=SeverityLevel.GREEN,
                reason="No safety signals detected",
                triggered_rules=[],
                confidence=0.99,
                layer="heuristic",
                metadata={"locale": locale, "message_length": len(message)},
            )

        non_exempt = [h for h in hits if not h.exempted]
        if not non_exempt:
            return ClassificationResult(
                severity=SeverityLevel.GREEN,
                reason="All signals exempted (quotation/joke/context)",
                triggered_rules=["exempted"],
                confidence=0.95,
                layer="heuristic",
                metadata={
                    "locale": locale,
                    "raw_hits": [
                        (h.pattern.category, h.match_text, h.pattern.severity_default) for h in hits
                    ],
                },
            )

        max_sev = max(non_exempt, key=lambda h: SeverityLevel(h.final_severity).ordinal)
        severity = SeverityLevel(max_sev.final_severity)

        triggered_categories = list(set(h.pattern.category for h in non_exempt))
        triggered_texts = [h.match_text for h in non_exempt]

        top_category = triggered_categories[0] if triggered_categories else "unknown"
        return ClassificationResult(
            severity=severity,
            reason=f"Layer 1: {top_category} signal detected",
            triggered_rules=triggered_categories,
            confidence=0.95 if severity == SeverityLevel.PURPLE else 0.85,
            layer="heuristic",
            metadata={
                "locale": locale,
                "matched_texts": triggered_texts,
                "categories": triggered_categories,
                "message_length": len(message),
            },
        )

    def _should_call_layer2(self, l1_result: ClassificationResult, message: str) -> bool:
        """Determine if Layer 2 LLM classification should be invoked."""
        if l1_result.severity == SeverityLevel.GREEN and len(message) > 50:
            return True
        if l1_result.severity == SeverityLevel.YELLOW and "despair" in l1_result.metadata.get(
            "categories", []
        ):
            return True
        if l1_result.severity == SeverityLevel.ORANGE:
            return True
        return False

    async def _llm_layer(
        self,
        message: str,
        l1_hint: ClassificationResult,
        model_router: Any,
    ) -> ClassificationResult:
        """Layer 2: LLM-based classification with 500ms timeout fallback."""
        try:
            async with asyncio.timeout(0.5):
                result = await self._call_llm(message, l1_hint, model_router)
                return result
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning(
                "safety_layer2_timeout_fallback",
                l1_severity=l1_hint.severity.value,
            )
            return l1_hint
        except Exception as exc:
            logger.error("safety_layer2_error_fallback", error=str(exc))
            return l1_hint

    async def _call_llm(
        self,
        message: str,
        l1_hint: ClassificationResult,
        model_router: Any,
    ) -> ClassificationResult:
        """Execute LLM classification via ModelRouter."""
        system_prompt = (
            "You are a safety classifier. Determine if the user message expresses "
            "suicidal intent, self-harm intent, or a clear threat of harm to others.\n"
            "Output ONLY one line of JSON: "
            '{"level": "GREEN|YELLOW|ORANGE|RED|PURPLE", '
            '"category": "suicide|self_harm|others_harm|abuse|despair|substance_abuse|none", '
            '"confidence": 0.0-1.0, "is_quotation": bool, "is_joke": bool}\n'
            "GREEN: no risk. YELLOW: possible distress. ORANGE: moderate risk. "
            "RED: high risk of harm to others or minor. PURPLE: imminent crisis.\n"
            "is_quotation: true if user is quoting someone or referencing fiction/lyrics.\n"
            "is_joke: true if the statement appears to be humor or sarcasm."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Layer 1 assessment: {l1_hint.severity.value}\n\nUser message: {message}"
                ),
            },
        ]

        try:
            raw = await model_router.call_cheap(
                messages=messages,
                temperature=0.0,
                max_tokens=64,
                json_mode=True,
                agent_name="safety_layer2",
            )
            parsed = self._parse_layer2_response(raw, l1_hint)
            return parsed
        except Exception as exc:
            logger.error("safety_layer2_llm_call_failed", error=str(exc))
            return l1_hint

    def _parse_layer2_response(
        self, raw: str, l1_hint: ClassificationResult
    ) -> ClassificationResult:
        """Parse LLM JSON response into ClassificationResult."""
        try:
            content = raw.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content)
        except (json.JSONDecodeError, IndexError):
            logger.warning("safety_layer2_json_parse_failed", raw=raw[:200])
            return l1_hint

        level_str = data.get("level", "GREEN").upper()
        category = data.get("category", "none")
        confidence = float(data.get("confidence", 0.5))
        is_quotation = bool(data.get("is_quotation", False))
        is_joke = bool(data.get("is_joke", False))

        try:
            severity = SeverityLevel(level_str)
        except ValueError:
            severity = SeverityLevel.GREEN

        if (is_quotation or is_joke) and severity == SeverityLevel.PURPLE:
            severity = SeverityLevel.YELLOW
            logger.info("safety_layer2_downgraded_quotation_joke", original_level=level_str)

        if severity.ordinal < l1_hint.severity.ordinal:
            severity = l1_hint.severity

        return ClassificationResult(
            severity=severity,
            reason=f"Layer 2: {category} (confidence={confidence:.2f})",
            triggered_rules=l1_hint.triggered_rules + [f"llm_{category}"],
            confidence=confidence,
            metadata={
                **l1_hint.metadata,
                "layer2_level": level_str,
                "layer2_category": category,
                "is_quotation": is_quotation,
                "is_joke": is_joke,
            },
            layer="llm",
        )

    def _extract_wellbeing_signals(
        self, result: ClassificationResult, message: str
    ) -> Dict[str, Any]:
        """Extract wellbeing signals from classification result for Layer 3."""
        categories = result.metadata.get("categories", [])
        triggered = set(result.triggered_rules)

        signals: Dict[str, Any] = {
            "severity": result.severity.value,
            "severity_ordinal": result.severity.ordinal,
        }

        if "despair" in categories or "despair" in triggered:
            signals["despair"] = 0.85
        else:
            loneliness_words = ["lonely", "alone", "孤独", "孤单", "孤独", "ひとり", "孤立"]
            for w in loneliness_words:
                if w.lower() in message.lower():
                    signals["loneliness"] = 0.7
                    break

        sleep_words = [
            "insomnia",
            "sleepless",
            "can't sleep",
            "cannot sleep",
            "失眠",
            "睡不着",
            "眠れな",
            "不眠",
            "寝れな",
        ]
        for w in sleep_words:
            if w.lower() in message.lower():
                signals["sleep_disturbance"] = 0.7
                break

        return signals

    def get_last_classification(
        self, user_id: UUID, character_id: str
    ) -> Optional[ClassificationResult]:
        """Retrieve the last classification for this user x character pair."""
        key = (str(user_id), character_id)
        return self._last_classification.get(key)

    def resolve_care_response(
        self,
        locale: str,
        jurisdiction: Optional[str] = None,
    ) -> str:
        """Resolve jurisdiction-aware PURPLE care path response text.

        Args:
            locale: Locale code ('zh', 'ja', 'en').
            jurisdiction: Jurisdiction code (e.g. 'CN', 'US', 'JP').

        Returns:
            Formatted care path response string, or default fallback.
        """
        care_path = self._loader.get_care_path(locale)
        if not care_path:
            for fallback_locale in [locale[:2], "en"]:
                care_path = self._loader.get_care_path(fallback_locale)
                if care_path:
                    break
        if not care_path:
            return (
                "I'm here for you. What you're feeling matters, and you don't "
                "have to go through it alone. Please reach out to someone you "
                "trust, or contact a mental health professional. "
                "If you're in immediate crisis, call 988 (US) or your local "
                "emergency services."
            )

        jurisdictions = care_path.get("jurisdictions", {})
        if jurisdiction and jurisdiction in jurisdictions:
            j_data = jurisdictions[jurisdiction]
        else:
            fallback_id = care_path.get("fallback_template_id", "")
            j_data = None
            for _j_key, j_val in jurisdictions.items():
                if j_val.get("template_id") == fallback_id:
                    j_data = j_val
                    break
            if j_data is None and jurisdictions:
                j_data = list(jurisdictions.values())[0]

        if j_data is None:
            return (
                "I'm here for you. What you're feeling matters, and you don't "
                "have to go through it alone. Please reach out to someone you "
                "trust, or contact a mental health professional."
            )

        text = j_data.get("text", "")
        text = text.replace("{hotline_name}", j_data.get("hotline_name", ""))
        text = text.replace("{hotline_number}", j_data.get("hotline_number", ""))
        text = text.replace("{hotline_hours}", j_data.get("hotline_hours", ""))
        return text.strip()
