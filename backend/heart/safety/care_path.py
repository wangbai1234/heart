"""
PURPLE Care Path — fixed-template OOC safety response.

Design: docs/design/purple_care_path.md
Spec:   runtime_specs/07_agent_orchestration.md §3.9

Triggers from:
  1. SafetyAgent.pre_filter() returns PURPLE_CARE_REQUIRED
  2. WellbeingMonitor has care_path_active = true + current turn non-GREEN
  3. Operator override (session.suicide_protocol_active = true)

Hard-bypasses: Director, Composer, LLM — no model call, Soul voice paused.
Renders: fixed OOC template per (locale, jurisdiction) from config/care_path_responses/.
Responds: single message envelope with kind="care_path_ooc" (not streamed).

Author: 心屿团队
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import yaml

logger = structlog.get_logger()

# ============================================================
# Resolve template directory relative to this file
# ============================================================

_CARE_PATH_DIR: Path = (
    Path(__file__).resolve().parents[3] / "config" / "care_path_responses"
)


# ============================================================
# Enums
# ============================================================


class TriggerSource(str, Enum):
    """What triggered the PURPLE Care Path (§1)."""

    SAFETY_PRE_FILTER = "safety_pre_filter"
    WELLBEING_MONITOR = "wellbeing_monitor"
    OPERATOR = "operator"


# ============================================================
# Data Models
# ============================================================


@dataclass(frozen=True)
class CarePathTemplate:
    """A parsed care-path response template from YAML (§3).

    Three OOC blocks:
      block_a_ooc:     "This message is from Heart Safety, not from..."
      block_b_resource: hotline + resource text
      block_c_resume:  "The character is still here..."
    """

    template_id: str
    locale: str
    jurisdiction: str
    spec_version: str

    block_a_ooc: str
    block_b_resource: str
    block_c_resume: str

    hotlines: tuple[dict[str, Any], ...] = ()

    # Minor variant fields
    has_minor_variant: bool = False
    minor_template_id: str = ""
    minor_block_b_resource: str = ""

    # File source for audit trail
    _source_file: str = ""

    @property
    def full_response(self) -> str:
        """Render the three blocks as a single text (with blank-line separation)."""
        return f"{self.block_a_ooc}\n\n{self.block_b_resource}\n\n{self.block_c_resume}"

    def response_for_minor(self) -> str:
        """Render response with minor variant Block B if available."""
        if self.has_minor_variant and self.minor_block_b_resource:
            b = self.minor_block_b_resource
        else:
            b = self.block_b_resource
        return f"{self.block_a_ooc}\n\n{b}\n\n{self.block_c_resume}"


@dataclass(frozen=True)
class ResolvedTemplate:
    """Result of template resolution (§4)."""

    template: CarePathTemplate
    locale: str
    jurisdiction: str
    resolution_path: str  # "exact" | "locale_default" | "en_intl" | "hardcoded"


@dataclass
class CarePathResponse:
    """The rendered PURPLE Care Path response sent to the user.

    Not streamed — sent as a single envelope with kind="care_path_ooc".
    """

    kind: str = "care_path_ooc"
    template_id: str = ""
    locale: str = ""
    jurisdiction: str = ""

    block_a_ooc: str = ""
    block_b_resource: str = ""
    block_c_resume: str = ""

    full_response: str = ""
    is_minor_variant: bool = False

    # For the client to render distinct visual frame
    envelope: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.full_response = (
            f"{self.block_a_ooc}\n\n{self.block_b_resource}\n\n{self.block_c_resume}"
        )
        self.envelope = {
            "kind": self.kind,
            "template_id": self.template_id,
            "locale": self.locale,
            "jurisdiction": self.jurisdiction,
            "blocks": {
                "a": self.block_a_ooc,
                "b": self.block_b_resource,
                "c": self.block_c_resume,
            },
            "is_minor_variant": self.is_minor_variant,
        }


@dataclass
class CarePathAuditEvent:
    """Audit record emitted when PURPLE Care Path activates (§5)."""

    user_id: str
    character_id: str = ""
    session_id: str = ""
    trace_id: str = ""

    triggered_by: TriggerSource = TriggerSource.SAFETY_PRE_FILTER
    message_hash: str = ""  # SHA-256 of user message (never raw text in event)
    classification_level: str = "PURPLE"

    classifier_chain: list[dict[str, Any]] = field(default_factory=list)

    template_id_selected: str = ""
    locale: str = ""
    jurisdiction: str = ""
    resolution_path: str = ""

    emitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    delivery_level: str = "at_least_once"

    # For content review team — not in the event bus payload
    _raw_message_ref: str = ""  # pointer to safety_classifications row, NOT raw text


# ============================================================
# Template Lint Validation (§4.3)
# ============================================================

# Tokens that signal Soul voice / roleplay drift — must NOT appear in OOC blocks
_BANNED_SOUL_TOKENS: tuple[str, ...] = (
    "凛",
    "桃乐丝",
    "桃桃",
    "Rin",
    "Dorothy",
    # Roleplay leak markers
    "*",
    "（......）",
    "(......)",
    # Forbidden affect language in OOC frame
    "I love you",
    "我爱你",
    "我担心你",
)


def _lint_template(tmpl: CarePathTemplate) -> list[str]:
    """Validate a template against lint rules.

    Returns a list of violation messages; empty list = pass.
    """
    violations: list[str] = []

    blocks = [
        ("block_a_ooc", tmpl.block_a_ooc),
        ("block_b_resource", tmpl.block_b_resource),
        ("block_c_resume", tmpl.block_c_resume),
    ]

    for block_name, text in blocks:
        for token in _BANNED_SOUL_TOKENS:
            if token in text:
                violations.append(
                    f"{block_name}: banned soul-voice token '{token}' found in OOC block"
                )

    # Check all three blocks are non-empty
    for block_name, text in blocks:
        if not text or not text.strip():
            violations.append(f"{block_name}: must not be empty")

    return violations


# ============================================================
# Template Loader (§4)
# ============================================================


class TemplateLoader:
    """Loads and caches care-path response templates.

    Resolution order (§4.1):
      1. exact (locale, jurisdiction)
      2. (locale, default_jurisdiction_for[locale])
      3. ("en", "INTL")
      4. HARDCODED_LAST_RESORT

    All templates are loaded at import time. Adding a new market =
    add a YAML + add a row to _routing.yaml, no code change.
    """

    # Default jurisdiction per locale when unresolvable
    _LOCALE_DEFAULTS: ClassVar[dict[str, str]] = {
        "zh-CN": "CN",
        "zh-HK": "HK",
        "zh-TW": "TW",
        "en": "US",
        "ja": "JP",
    }

    # In-memory template cache: (locale, jurisdiction) → CarePathTemplate
    _templates: ClassVar[dict[tuple[str, str], CarePathTemplate]] = {}

    _loaded: ClassVar[bool] = False
    _load_errors: ClassVar[list[str]] = []

    @classmethod
    def load_all(cls) -> None:
        """Load all templates from config/care_path_responses/.

        Called once at import. The service MUST refuse to start if
        HARDCODED_LAST_RESORT is missing.
        """
        if cls._loaded:
            return

        routing_path = _CARE_PATH_DIR / "_routing.yaml"
        if not routing_path.exists():
            msg = (
                "FATAL: _routing.yaml not found at %s; "
                "PURPLE Care Path cannot operate"
            )
            logger.critical(msg, routing_path)
            cls._load_errors.append(msg % routing_path)
            cls._loaded = True
            return

        with open(routing_path, encoding="utf-8") as fh:
            routing = yaml.safe_load(fh) or {}

        for entry in routing.get("templates", []):
            locale = entry["locale"]
            jurisdiction = entry["jurisdiction"]
            file_name = entry["file"]
            file_path = _CARE_PATH_DIR / file_name

            try:
                tmpl = cls._parse_template_file(file_path)
                cls._templates[(locale, jurisdiction)] = tmpl
                logger.debug(
                    "Loaded care-path template %s for (%s, %s)",
                    tmpl.template_id, locale, jurisdiction,
                )
            except Exception:
                msg = "Failed to load care-path template %s for (%s, %s)"
                logger.exception(msg, file_path, locale, jurisdiction)
                cls._load_errors.append(msg % (file_path, locale, jurisdiction))

        # Verify HARDCODED_LAST_RESORT
        last_resort = cls._templates.get(("en", "INTL"))
        if last_resort is None:
            err = (
                "FATAL: no (en, INTL) template loaded; "
                "HARDCODED_LAST_RESORT is required for PURPLE Care Path"
            )
            logger.critical(err)
            cls._load_errors.append(err)

        cls._loaded = True

        loaded_count = len(cls._templates)
        if cls._load_errors:
            logger.warning(
                "Care-path templates loaded: %d templates, %d errors",
                loaded_count, len(cls._load_errors),
            )
        else:
            logger.info(
                "Care-path templates loaded: %d templates, 0 errors",
                loaded_count,
            )

    @classmethod
    def resolve(
        cls,
        locale: str,
        jurisdiction: str,
        is_minor: bool = False,
    ) -> ResolvedTemplate:
        """Resolve a template for the given (locale, jurisdiction).

        Args:
            locale: User's locale (e.g., "zh-CN", "en", "ja").
            jurisdiction: Country code (e.g., "CN", "US", "JP").
            is_minor: If True and a minor variant exists, use it.

        Returns:
            ResolvedTemplate with the selected template and resolution metadata.

        Raises:
            RuntimeError: If no template could be resolved (should never
                happen if HARDCODED_LAST_RESORT exists at startup).
        """
        if not cls._loaded:
            cls.load_all()

        locale_key = locale
        jurisdiction_key = jurisdiction.upper() if jurisdiction else ""

        # 1. Exact match
        key = (locale_key, jurisdiction_key)
        if key in cls._templates:
            return ResolvedTemplate(
                template=cls._templates[key],
                locale=locale_key,
                jurisdiction=jurisdiction_key,
                resolution_path="exact",
            )

        # 2. Locale default jurisdiction
        default_jur = cls._LOCALE_DEFAULTS.get(locale_key)
        if default_jur:
            key = (locale_key, default_jur)
            if key in cls._templates:
                return ResolvedTemplate(
                    template=cls._templates[key],
                    locale=locale_key,
                    jurisdiction=default_jur,
                    resolution_path="locale_default",
                )

        # Also try stripped locale (e.g., "zh-CN" → "zh")
        if "-" in locale_key:
            base_locale = locale_key.split("-")[0]
            default_jur = cls._LOCALE_DEFAULTS.get(base_locale)
            if default_jur:
                key = (base_locale, default_jur)
                if key in cls._templates:
                    return ResolvedTemplate(
                        template=cls._templates[key],
                        locale=base_locale,
                        jurisdiction=default_jur,
                        resolution_path="locale_default",
                    )

        # 3. en / INTL fallback
        key = ("en", "INTL")
        if key in cls._templates:
            logger.warning(
                "Care-path fallback to en/INTL for locale=%s jurisdiction=%s",
                locale, jurisdiction,
            )
            return ResolvedTemplate(
                template=cls._templates[key],
                locale="en",
                jurisdiction="INTL",
                resolution_path="en_intl",
            )

        # 4. Should never reach here — HARDCODED_LAST_RESORT checked at startup
        raise RuntimeError(
            "PURPLE Care Path: no template resolvable for "
            f"locale={locale} jurisdiction={jurisdiction}; "
            "HARDCODED_LAST_RESORT missing at startup"
        )

    @classmethod
    def get_loaded_count(cls) -> int:
        """Return the number of loaded templates (for health checks)."""
        return len(cls._templates)

    @classmethod
    def get_load_errors(cls) -> list[str]:
        """Return load-time errors (for health checks)."""
        return list(cls._load_errors)

    # -------- internal --------

    @classmethod
    def _parse_template_file(cls, path: Path) -> CarePathTemplate:
        """Parse a single template YAML file."""
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        # Parse hotlines
        hotlines: list[dict[str, Any]] = []
        for h in raw.get("hotlines", []) or []:
            hotlines.append({
                "name": h.get("name", ""),
                "number": h.get("number", ""),
                "format": h.get("format", ""),
                "hours": h.get("hours", ""),
                "modes": h.get("modes", []),
                "languages": h.get("languages", []),
                "source_url": h.get("source_url", ""),
                "last_verified": h.get("last_verified", ""),
            })

        # Parse minor variant
        minor_raw = raw.get("minor_variant") or {}
        has_minor = minor_raw.get("enabled", False)
        minor_template_id = minor_raw.get("template_id", "")
        minor_block_b = minor_raw.get("block_b_resource_text", "")

        # Extract block texts
        block_a = (raw.get("block_a_ooc") or {}).get("text", "").strip()
        block_b = (raw.get("block_b_resource") or {}).get("text", "").strip()
        block_c = (raw.get("block_c_resume") or {}).get("text", "").strip()

        return CarePathTemplate(
            template_id=raw.get("template_id", path.stem),
            locale=raw.get("locale", ""),
            jurisdiction=raw.get("jurisdiction", ""),
            spec_version=raw.get("spec_version", ""),
            block_a_ooc=block_a,
            block_b_resource=block_b,
            block_c_resume=block_c,
            hotlines=tuple(hotlines),
            has_minor_variant=has_minor,
            minor_template_id=minor_template_id,
            minor_block_b_resource=minor_block_b,
            _source_file=str(path),
        )


# ============================================================
# Care Path Engine (§1–§5)
# ============================================================


@dataclass
class CarePathEngine:
    """PURPLE Care Path engine.

    Usage::

        engine = CarePathEngine(event_bus=eb, metrics=prom_counter)
        if engine.should_activate(safety_level="PURPLE", ...):
            response = engine.render(locale="zh-CN", jurisdiction="CN")
            engine.emit_audit(audit_event)
            # Send response to user
    """

    # Optional dependencies (injected, not imported at module level)
    event_bus: Any = None  # heart.infra.event_bus.EventBus
    metrics_counter: Any = None  # Prometheus Counter or mock
    alert_callback: Any = None  # callable for content review team paging

    # Audit log storage (in-memory for MVP; replace with DB writer)
    audit_log: list[CarePathAuditEvent] = field(default_factory=list, init=False)

    # ---- Trigger Detection (§1) ----

    @staticmethod
    def should_activate(
        safety_level: str = "",
        wellbeing_care_path_active: bool = False,
        current_turn_safety_green: bool = True,
        operator_override: bool = False,
    ) -> tuple[bool, TriggerSource | None]:
        """Check if PURPLE Care Path should activate for this turn.

        OR-logic: any of the three trigger conditions is sufficient.

        Args:
            safety_level: From safety pre_filter (e.g., "PURPLE_CARE_REQUIRED").
            wellbeing_care_path_active: WBM directive care_path_active flag.
            current_turn_safety_green: Whether current turn is safe (GREEN/NONE).
            operator_override: session.suicide_protocol_active from admin tool.

        Returns:
            (should_activate, trigger_source)
        """
        # 1. Safety Agent pre_filter
        if safety_level in ("PURPLE_CARE_REQUIRED", "PURPLE"):
            return True, TriggerSource.SAFETY_PRE_FILTER

        # 2. Wellbeing Monitor active + non-GREEN turn
        if wellbeing_care_path_active and not current_turn_safety_green:
            return True, TriggerSource.WELLBEING_MONITOR

        # 3. Operator override
        if operator_override:
            return True, TriggerSource.OPERATOR

        return False, None

    # ---- Response Rendering (§3) ----

    def render(
        self,
        locale: str = "en",
        jurisdiction: str = "US",
        is_minor: bool = False,
    ) -> CarePathResponse:
        """Render the PURPLE Care Path response.

        Args:
            locale: User's locale.
            jurisdiction: User's jurisdiction (country code).
            is_minor: If True, use minor variant when available.

        Returns:
            CarePathResponse with Blocks A/B/C and the full rendered text.
        """
        resolved = TemplateLoader.resolve(locale, jurisdiction, is_minor=is_minor)
        tmpl = resolved.template

        use_minor = is_minor and tmpl.has_minor_variant

        block_b = tmpl.minor_block_b_resource if use_minor else tmpl.block_b_resource

        return CarePathResponse(
            kind="care_path_ooc",
            template_id=tmpl.template_id,
            locale=resolved.locale,
            jurisdiction=resolved.jurisdiction,
            block_a_ooc=tmpl.block_a_ooc,
            block_b_resource=block_b,
            block_c_resume=tmpl.block_c_resume,
            is_minor_variant=use_minor,
        )

    # ---- Audit Event Emission (§5) ----

    def build_audit_event(
        self,
        user_id: str,
        triggered_by: TriggerSource,
        message_hash: str = "",
        character_id: str = "",
        session_id: str = "",
        trace_id: str = "",
        classifier_chain: list[dict[str, Any]] | None = None,
        response: CarePathResponse | None = None,
    ) -> CarePathAuditEvent:
        """Construct an audit event for the current PURPLE activation.

        The raw user message is NEVER included in the event body (§5.1).
        Only the SHA-256 hash is carried. Raw text goes to the audited
        safety_classifications store under access control.
        """
        return CarePathAuditEvent(
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
            trace_id=trace_id,
            triggered_by=triggered_by,
            message_hash=message_hash,
            classification_level="PURPLE",
            classifier_chain=classifier_chain or [],
            template_id_selected=response.template_id if response else "",
            locale=response.locale if response else "",
            jurisdiction=response.jurisdiction if response else "",
            emitted_at=datetime.now(timezone.utc).isoformat(),
            delivery_level="at_least_once",
        )

    def emit_audit(self, event: CarePathAuditEvent) -> None:
        """Emit the audit event to all configured sinks.

        Fire-and-forget: if any sink fails, the user still gets the care response.
        """
        self.audit_log.append(event)

        # 1. Event bus — safety.purple.detected
        if self.event_bus is not None:
            try:
                import asyncio

                payload = {
                    "user_id": event.user_id,
                    "character_id": event.character_id,
                    "session_id": event.session_id,
                    "trace_id": event.trace_id,
                    "triggered_by": event.triggered_by.value,
                    "message_hash": event.message_hash,
                    "classification_level": event.classification_level,
                    "classifier_chain": event.classifier_chain,
                    "template_id_selected": event.template_id_selected,
                    "locale": event.locale,
                    "jurisdiction": event.jurisdiction,
                    "emitted_at": event.emitted_at,
                    "delivery_level": event.delivery_level,
                }

                if asyncio.iscoroutinefunction(self.event_bus.emit):
                    logger.info(
                        "safety.purple.detected (async emit pending) user=%s",
                        event.user_id,
                    )
                else:
                    self.event_bus.emit("safety.purple.detected", payload)
                    logger.info(
                        "safety.purple.detected user=%s template=%s",
                        event.user_id, event.template_id_selected,
                    )
            except Exception:
                logger.exception(
                    "Failed to emit safety.purple.detected for user=%s",
                    event.user_id,
                )

        # 2. Prometheus counter
        if self.metrics_counter is not None:
            try:
                self.metrics_counter.labels(
                    triggered_by=event.triggered_by.value,
                    template_id=event.template_id_selected,
                    jurisdiction=event.jurisdiction,
                ).inc()
            except Exception:
                logger.exception("Failed to increment PURPLE care path metrics counter")

        # 3. Content review alert (callback)
        if self.alert_callback is not None:
            try:
                self.alert_callback(event)
            except Exception:
                logger.exception("PURPLE alert callback failed for user=%s", event.user_id)

        logger.info(
            "PURPLE Care Path audit emitted: user=%s trigger=%s template=%s "
            "locale=%s/%s",
            event.user_id,
            event.triggered_by.value,
            event.template_id_selected,
            event.locale,
            event.jurisdiction,
        )


# ============================================================
# Module-level init — eager-load templates
# ============================================================

# Load all templates at import time so resolution is O(1) at runtime.
TemplateLoader.load_all()


# ============================================================
# Public helpers
# ============================================================


def get_care_path_engine(
    event_bus: Any = None,
    metrics_counter: Any = None,
    alert_callback: Any = None,
) -> CarePathEngine:
    """Factory for CarePathEngine with optional dependencies injected."""
    return CarePathEngine(
        event_bus=event_bus,
        metrics_counter=metrics_counter,
        alert_callback=alert_callback,
    )


def validate_all_templates() -> list[str]:
    """Run lint validation on all loaded templates (§4.3).

    Returns:
        List of violation messages across all templates; empty = all clear.
    """
    violations: list[str] = []
    for (locale, jurisdiction), tmpl in TemplateLoader._templates.items():
        errs = _lint_template(tmpl)
        for e in errs:
            violations.append(f"[{locale}/{jurisdiction}] {e}")
    return violations


def get_template_count() -> int:
    """Return the number of loaded care-path templates (for health checks)."""
    return TemplateLoader.get_loaded_count()


def get_load_errors() -> list[str]:
    """Return template load-time errors (for health checks)."""
    return TemplateLoader.get_load_errors()
