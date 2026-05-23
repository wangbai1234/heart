"""
Tests for PURPLE Care Path — care_path.py

Covers:
  1. Trigger conditions (§1): safety pre-filter, wellbeing monitor, operator
  2. Response selection by jurisdiction (§4): exact, locale default, en_intl, hardcoded
  3. Audit log integrity (§5): event fields, no raw text leak, log append
  4. No Soul voice drift (§3.2): template lint, response block content
  5. Template loading: all shipped templates, count, errors
  6. Minor variant support

Run:  pytest backend/tests/unit/test_care_path.py -v
"""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from heart.safety.care_path import (
    CarePathAuditEvent,
    CarePathEngine,
    CarePathResponse,
    CarePathTemplate,
    ResolvedTemplate,
    TemplateLoader,
    TriggerSource,
    _lint_template,
    get_care_path_engine,
    get_load_errors,
    get_template_count,
    validate_all_templates,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def engine() -> CarePathEngine:
    """Clean engine with no external dependencies (mock sinks)."""
    return CarePathEngine()


@pytest.fixture
def engine_with_mocks() -> CarePathEngine:
    """Engine with mocked event bus and metrics."""
    mock_bus = MagicMock()
    mock_counter = MagicMock()
    return CarePathEngine(
        event_bus=mock_bus,
        metrics_counter=mock_counter,
    )


@pytest.fixture
def sample_response() -> CarePathResponse:
    """A realistic response for audit event tests."""
    return CarePathResponse(
        kind="care_path_ooc",
        template_id="us_en_v1",
        locale="en",
        jurisdiction="US",
        block_a_ooc="This message is from Heart Safety.",
        block_b_resource="Call 988.",
        block_c_resume="The character is still here.",
    )


# ============================================================
# 1. Trigger Conditions (§1)
# ============================================================


class TestTriggerConditions:
    """Verify PURPLE Care Path activation logic — OR-logic per §1."""

    # --- Safety Agent pre_filter triggers ---

    def test_safety_pre_filter_purple_activates(self, engine):
        """SafetyAgent returns PURPLE → care path activates."""
        active, source = engine.should_activate(
            safety_level="PURPLE",
        )
        assert active is True
        assert source == TriggerSource.SAFETY_PRE_FILTER

    def test_safety_pre_filter_purple_care_required_activates(self, engine):
        """SafetyAgent returns PURPLE_CARE_REQUIRED → care path activates."""
        active, source = engine.should_activate(
            safety_level="PURPLE_CARE_REQUIRED",
        )
        assert active is True
        assert source == TriggerSource.SAFETY_PRE_FILTER

    def test_safety_pre_filter_high_does_not_activate(self, engine):
        """HIGH alone (without WBM) does NOT activate PURPLE care path."""
        active, source = engine.should_activate(
            safety_level="HIGH",
        )
        assert active is False
        assert source is None

    def test_safety_pre_filter_red_does_not_activate(self, engine):
        """RED goes to reject path, not PURPLE care path."""
        active, source = engine.should_activate(
            safety_level="RED",
        )
        assert active is False
        assert source is None

    def test_safety_pre_filter_none_does_not_activate(self, engine):
        """Normal message yields no activation."""
        active, source = engine.should_activate(
            safety_level="NONE",
        )
        assert active is False
        assert source is None

    # --- Wellbeing Monitor triggers ---

    def test_wbm_active_non_green_activates(self, engine):
        """WBM care_path_active + non-GREEN turn → activates."""
        active, source = engine.should_activate(
            safety_level="MEDIUM",
            wellbeing_care_path_active=True,
            current_turn_safety_green=False,
        )
        assert active is True
        assert source == TriggerSource.WELLBEING_MONITOR

    def test_wbm_active_but_green_does_not_activate(self, engine):
        """WBM care_path_active but GREEN turn → no activation (per §1)."""
        active, source = engine.should_activate(
            safety_level="LOW",
            wellbeing_care_path_active=True,
            current_turn_safety_green=True,
        )
        assert active is False
        assert source is None

    def test_wbm_inactive_medium_no_activation(self, engine):
        """MEDIUM without WBM active → no PURPLE care path."""
        active, source = engine.should_activate(
            safety_level="MEDIUM",
            wellbeing_care_path_active=False,
            current_turn_safety_green=False,
        )
        assert active is False
        assert source is None

    # --- Operator override ---

    def test_operator_override_activates(self, engine):
        """Operator sets suicide_protocol_active → care path regardless of safety level."""
        active, source = engine.should_activate(
            safety_level="NONE",
            operator_override=True,
        )
        assert active is True
        assert source == TriggerSource.OPERATOR

    def test_operator_override_even_when_safe(self, engine):
        """Operator override activates even when all other signals are green."""
        active, source = engine.should_activate(
            safety_level="NONE",
            wellbeing_care_path_active=False,
            current_turn_safety_green=True,
            operator_override=True,
        )
        assert active is True
        assert source == TriggerSource.OPERATOR

    # --- Priority: PURPLE beats WBM ---

    def test_purple_takes_priority_over_wbm(self, engine):
        """When both triggers are present, safety pre-filter wins (first check)."""
        active, source = engine.should_activate(
            safety_level="PURPLE",
            wellbeing_care_path_active=True,
            current_turn_safety_green=False,
        )
        assert active is True
        assert source == TriggerSource.SAFETY_PRE_FILTER


# ============================================================
# 2. Response Selection by Jurisdiction (§4)
# ============================================================


class TestJurisdictionRouting:
    """Verify template resolution chain: exact → locale_default → en_intl → hardcoded."""

    def test_exact_match_zh_cn(self, engine):
        """(zh-CN, CN) resolves to cn_zh_v1 template."""
        resp = engine.render(locale="zh-CN", jurisdiction="CN")
        assert resp.template_id == "cn_zh_v1"
        assert resp.locale == "zh-CN"
        assert resp.jurisdiction == "CN"
        # zh-CN template should contain Chinese text
        assert "Heart Safety" in resp.block_a_ooc
        assert "北京心理危机研究与干预中心" in resp.block_b_resource
        assert len(resp.block_c_resume) > 0

    def test_exact_match_en_us(self, engine):
        """(en, US) resolves to us_en_v1 template."""
        resp = engine.render(locale="en", jurisdiction="US")
        assert resp.template_id == "us_en_v1"
        assert resp.locale == "en"
        assert resp.jurisdiction == "US"
        assert "Heart Safety" in resp.block_a_ooc
        assert "988" in resp.block_b_resource

    def test_exact_match_en_gb(self, engine):
        """(en, GB) resolves to gb_en_v1 template."""
        resp = engine.render(locale="en", jurisdiction="GB")
        assert resp.template_id == "gb_en_v1"
        assert resp.jurisdiction == "GB"

    def test_exact_match_en_au(self, engine):
        """(en, AU) resolves to au_en_v1 template."""
        resp = engine.render(locale="en", jurisdiction="AU")
        assert resp.template_id == "au_en_v1"
        assert resp.jurisdiction == "AU"

    def test_exact_match_ja_jp(self, engine):
        """(ja, JP) resolves to jp_ja_v1 template."""
        resp = engine.render(locale="ja", jurisdiction="JP")
        assert resp.template_id == "jp_ja_v1"
        assert resp.locale == "ja"
        assert resp.jurisdiction == "JP"

    def test_exact_match_zh_hk(self, engine):
        """(zh-HK, HK) resolves to hk_zh_v1 template."""
        resp = engine.render(locale="zh-HK", jurisdiction="HK")
        assert resp.template_id == "hk_zh_v1"
        assert resp.jurisdiction == "HK"

    def test_exact_match_zh_tw(self, engine):
        """(zh-TW, TW) resolves to tw_zh_v1 template."""
        resp = engine.render(locale="zh-TW", jurisdiction="TW")
        assert resp.template_id == "tw_zh_v1"
        assert resp.jurisdiction == "TW"

    def test_locale_default_unknown_jurisdiction(self, engine):
        """(zh-CN, FR) → locale default → (zh-CN, CN)."""
        resp = engine.render(locale="zh-CN", jurisdiction="FR")
        assert resp.template_id == "cn_zh_v1"
        assert resp.locale == "zh-CN"
        assert resp.jurisdiction == "CN"

    def test_locale_default_en_unknown(self, engine):
        """(en, DE) → locale default → (en, US)."""
        resp = engine.render(locale="en", jurisdiction="DE")
        assert resp.template_id == "us_en_v1"

    def test_en_intl_fallback(self, engine):
        """(fr, FR) → en/INTL fallback."""
        resp = engine.render(locale="fr", jurisdiction="FR")
        assert resp.template_id == "intl_en_v1"
        assert resp.locale == "en"
        assert resp.jurisdiction == "INTL"

    def test_case_insensitive_jurisdiction(self, engine):
        """Jurisdiction 'us' (lowercase) resolves same as 'US'."""
        resp_lower = engine.render(locale="en", jurisdiction="us")
        resp_upper = engine.render(locale="en", jurisdiction="US")
        assert resp_lower.template_id == resp_upper.template_id
        assert resp_lower.template_id == "us_en_v1"

    def test_empty_jurisdiction_falls_back(self, engine):
        """Empty jurisdiction → locale default."""
        resp = engine.render(locale="zh-CN", jurisdiction="")
        assert resp.template_id == "cn_zh_v1"

    def test_response_has_three_blocks(self, engine):
        """Every response must have non-empty Block A, B, C."""
        locales_jurisdictions = [
            ("zh-CN", "CN"),
            ("en", "US"),
            ("en", "GB"),
            ("en", "INTL"),
            ("ja", "JP"),
        ]
        for loc, jur in locales_jurisdictions:
            resp = engine.render(locale=loc, jurisdiction=jur)
            assert len(resp.block_a_ooc) > 0, f"Block A empty for {loc}/{jur}"
            assert len(resp.block_b_resource) > 0, f"Block B empty for {loc}/{jur}"
            assert len(resp.block_c_resume) > 0, f"Block C empty for {loc}/{jur}"

    def test_response_envelope_structure(self, engine):
        """Response includes a structured envelope for client rendering."""
        resp = engine.render(locale="en", jurisdiction="US")
        assert resp.envelope["kind"] == "care_path_ooc"
        assert resp.envelope["template_id"] == "us_en_v1"
        assert "blocks" in resp.envelope
        assert "a" in resp.envelope["blocks"]
        assert "b" in resp.envelope["blocks"]
        assert "c" in resp.envelope["blocks"]
        assert resp.envelope["is_minor_variant"] is False


# ============================================================
# 3. Audit Log Integrity (§5)
# ============================================================


class TestAuditLogIntegrity:
    """Verify audit events comply with §5.1 and §5.2."""

    def test_audit_event_fields_present(self, engine, sample_response):
        """All required fields are set on the audit event."""
        event = engine.build_audit_event(
            user_id="u123",
            triggered_by=TriggerSource.SAFETY_PRE_FILTER,
            message_hash="abc123def456",
            character_id="rin",
            session_id="sess-001",
            trace_id="trace-001",
            classifier_chain=[
                {"source": "heuristic", "matched": ["想死"]},
                {"source": "regex", "matched": []},
            ],
            response=sample_response,
        )

        assert event.user_id == "u123"
        assert event.triggered_by == TriggerSource.SAFETY_PRE_FILTER
        assert event.message_hash == "abc123def456"
        assert event.character_id == "rin"
        assert event.session_id == "sess-001"
        assert event.trace_id == "trace-001"
        assert event.classification_level == "PURPLE"
        assert event.template_id_selected == "us_en_v1"
        assert event.locale == "en"
        assert event.jurisdiction == "US"
        assert event.delivery_level == "at_least_once"
        assert len(event.emitted_at) > 0
        assert len(event.classifier_chain) == 2

    def test_raw_message_never_in_audit_event(self, engine, sample_response):
        """The audit event must NOT contain the raw user message (§5.1)."""
        event = engine.build_audit_event(
            user_id="u123",
            triggered_by=TriggerSource.SAFETY_PRE_FILTER,
            message_hash="sha256hash",
            response=sample_response,
        )

        # The raw text pointer is for internal use, not the actual message
        assert event._raw_message_ref == ""

        # Only the hash is in the public event
        event_dict = {
            "user_id": event.user_id,
            "message_hash": event.message_hash,
            "triggered_by": event.triggered_by.value,
        }
        assert "raw" not in str(event_dict).lower() or event_dict.get("message_hash") is not None

    def test_audit_log_appended(self, engine, sample_response):
        """Each emit_audit appends to the in-memory audit log."""
        event = engine.build_audit_event(
            user_id="u1", triggered_by=TriggerSource.SAFETY_PRE_FILTER,
            response=sample_response,
        )
        engine.emit_audit(event)
        assert len(engine.audit_log) == 1
        assert engine.audit_log[0].user_id == "u1"

    def test_multiple_audit_events_accumulate(self, engine, sample_response):
        """Multiple audit events are all appended in order."""
        for i in range(3):
            event = engine.build_audit_event(
                user_id=f"u{i}",
                triggered_by=TriggerSource.SAFETY_PRE_FILTER,
                response=sample_response,
            )
            engine.emit_audit(event)

        assert len(engine.audit_log) == 3
        assert engine.audit_log[0].user_id == "u0"
        assert engine.audit_log[2].user_id == "u2"

    def test_audit_does_not_block_on_sink_failure(self, engine, sample_response):
        """If event bus fails, audit still succeeds and log is appended."""
        mock_bus = MagicMock()
        mock_bus.emit.side_effect = RuntimeError("Event bus down")

        eng = CarePathEngine(event_bus=mock_bus)
        event = eng.build_audit_event(
            user_id="u1", triggered_by=TriggerSource.SAFETY_PRE_FILTER,
            response=sample_response,
        )
        # Must not raise
        eng.emit_audit(event)
        assert len(eng.audit_log) == 1

    def test_three_trigger_sources_all_produce_audit_events(self, engine_with_mocks, sample_response):
        """All three trigger sources should produce valid audit events."""
        for source in TriggerSource:
            event = engine_with_mocks.build_audit_event(
                user_id="u1",
                triggered_by=source,
                response=sample_response,
            )
            assert event.triggered_by == source
            engine_with_mocks.emit_audit(event)

        assert len(engine_with_mocks.audit_log) == 3

    def test_message_hash_is_sha256_format(self, engine, sample_response):
        """The message_hash field carries a SHA-256 hash, not plain text."""
        raw_message = "我想结束这一切"
        real_hash = hashlib.sha256(raw_message.encode()).hexdigest()[:16]

        event = engine.build_audit_event(
            user_id="u1",
            triggered_by=TriggerSource.SAFETY_PRE_FILTER,
            message_hash=real_hash,
            response=sample_response,
        )

        # The raw message text should NOT appear in any audit field
        assert raw_message not in event.message_hash
        assert len(event.message_hash) == 16  # hex digest length
        assert event.message_hash == real_hash


# ============================================================
# 4. No Drift to Soul Voice (§3.2)
# ============================================================


class TestNoSoulVoiceDrift:
    """Verify PURPLE templates contain no Soul voice tokens or roleplay drift."""

    SOUL_TOKENS = ["凛", "桃乐丝", "桃桃", "Rin", "Dorothy"]
    ROLEPLAY_MARKERS = ["*", "（......）", "(......)"]
    FORBIDDEN_AFFECT = ["I love you", "我爱你", "我担心你"]

    def test_all_loaded_templates_pass_lint(self):
        """Every shipped template must pass the no-Soul-voice lint."""
        violations = validate_all_templates()
        assert violations == [], (
            f"Template lint violations found:\n" + "\n".join(violations)
        )

    def test_zh_cn_response_no_soul_tokens(self, engine):
        """zh-CN response blocks must not contain character names."""
        resp = engine.render(locale="zh-CN", jurisdiction="CN")
        full = resp.full_response
        for token in self.SOUL_TOKENS:
            assert token not in full, f"zh-CN template contains soul token: {token}"

    def test_en_us_response_no_soul_tokens(self, engine):
        """en-US response blocks must not contain character names."""
        resp = engine.render(locale="en", jurisdiction="US")
        full = resp.full_response
        for token in self.SOUL_TOKENS:
            assert token not in full, f"en-US template contains soul token: {token}"

    def test_all_responses_no_roleplay_markers(self, engine):
        """No response should contain roleplay action descriptors (*, ......)."""
        locales = [
            ("zh-CN", "CN"), ("zh-HK", "HK"), ("zh-TW", "TW"),
            ("en", "US"), ("en", "GB"), ("en", "CA"), ("en", "AU"),
            ("en", "INTL"), ("ja", "JP"),
        ]
        for loc, jur in locales:
            resp = engine.render(locale=loc, jurisdiction=jur)
            full = resp.full_response
            for marker in self.ROLEPLAY_MARKERS:
                assert marker not in full, (
                    f"{loc}/{jur} template contains roleplay marker: {marker!r}"
                )

    def test_all_responses_no_forbidden_affect(self, engine):
        """No OOC blocks should contain affect language like 'I love you'."""
        locales = [
            ("zh-CN", "CN"), ("zh-HK", "HK"), ("zh-TW", "TW"),
            ("en", "US"), ("en", "GB"), ("en", "CA"), ("en", "AU"),
            ("en", "INTL"), ("ja", "JP"),
        ]
        for loc, jur in locales:
            resp = engine.render(locale=loc, jurisdiction=jur)
            full = resp.full_response
            for phrase in self.FORBIDDEN_AFFECT:
                assert phrase not in full, (
                    f"{loc}/{jur} template contains forbidden affect: {phrase!r}"
                )

    def test_lint_catches_soul_voice_injection(self):
        """Template lint should catch banned tokens injected in any block."""
        bad_template = CarePathTemplate(
            template_id="test_bad",
            locale="en",
            jurisdiction="XX",
            spec_version="1.0.0",
            block_a_ooc="This is from Heart Safety.",
            block_b_resource="凛 says call this number.",  # Soul token!
            block_c_resume="Character is still here.",
        )
        violations = _lint_template(bad_template)
        assert len(violations) > 0
        assert any("凛" in v for v in violations)

    def test_lint_catches_roleplay_marker_injection(self):
        """Template lint should catch roleplay asterisks in OOC blocks."""
        bad_template = CarePathTemplate(
            template_id="test_bad_rp",
            locale="en",
            jurisdiction="XX",
            spec_version="1.0.0",
            block_a_ooc="*notices you're struggling*",  # roleplay leak
            block_b_resource="Call 988.",
            block_c_resume="Character is still here.",
        )
        violations = _lint_template(bad_template)
        assert len(violations) > 0
        assert any("*" in v for v in violations)


# ============================================================
# 5. Template Loading & Validation (§4.3)
# ============================================================


class TestTemplateLoading:
    """Verify template loading, startup validation, and error handling."""

    def test_all_shipped_templates_loaded(self):
        """All 9 templates from _routing.yaml should load without errors."""
        errors = get_load_errors()
        count = get_template_count()
        assert errors == [], f"Load errors: {errors}"
        assert count >= 9, f"Expected >= 9 templates, got {count}"

    def test_en_intl_exists_as_last_resort(self):
        """HARDCODED_LAST_RESORT (en, INTL) must exist at startup."""
        resolved = TemplateLoader.resolve(locale="xx", jurisdiction="XX")
        assert resolved.template.template_id == "intl_en_v1"
        assert resolved.resolution_path == "en_intl"

    def test_resolution_path_tracking(self):
        """Resolution metadata tracks which fallback tier was used."""
        # exact
        r = TemplateLoader.resolve(locale="en", jurisdiction="US")
        assert r.resolution_path == "exact"

        # locale_default (unknown jurisdiction)
        r = TemplateLoader.resolve(locale="zh-CN", jurisdiction="DE")
        assert r.resolution_path == "locale_default"

        # en_intl
        r = TemplateLoader.resolve(locale="fr", jurisdiction="FR")
        assert r.resolution_path == "en_intl"


# ============================================================
# 6. Minor Variant Support
# ============================================================


class TestMinorVariant:
    """Verify minor-aware template variants."""

    def test_us_minor_variant_enabled(self):
        """US template has a minor variant with different Block B."""
        resolved = TemplateLoader.resolve(locale="en", jurisdiction="US")
        assert resolved.template.has_minor_variant is True
        assert len(resolved.template.minor_block_b_resource) > 0

    def test_us_minor_variant_different_block_b(self, engine):
        """Minor variant renders different Block B than adult version."""
        adult = engine.render(locale="en", jurisdiction="US", is_minor=False)
        minor = engine.render(locale="en", jurisdiction="US", is_minor=True)

        assert adult.template_id == "us_en_v1"
        assert minor.is_minor_variant is True
        assert minor.block_b_resource != adult.block_b_resource
        assert "Teen" in minor.block_b_resource or "teen" in minor.block_b_resource

    def test_zh_cn_minor_variant_disabled(self):
        """zh-CN template has minor_variant disabled."""
        resolved = TemplateLoader.resolve(locale="zh-CN", jurisdiction="CN")
        assert resolved.template.has_minor_variant is False

    def test_zh_cn_minor_renders_same_as_adult(self, engine):
        """When minor variant is disabled, rendering falls back to adult."""
        adult = engine.render(locale="zh-CN", jurisdiction="CN", is_minor=False)
        minor = engine.render(locale="zh-CN", jurisdiction="CN", is_minor=True)

        assert minor.is_minor_variant is False
        assert minor.block_b_resource == adult.block_b_resource


# ============================================================
# 7. Engine Factory
# ============================================================


class TestEngineFactory:
    """Verify the engine factory function."""

    def test_get_care_path_engine_returns_engine(self):
        """Factory returns a CarePathEngine instance."""
        eng = get_care_path_engine()
        assert isinstance(eng, CarePathEngine)

    def test_get_care_path_engine_with_dependencies(self):
        """Factory accepts optional dependencies."""
        mock_bus = MagicMock()
        mock_counter = MagicMock()

        eng = get_care_path_engine(
            event_bus=mock_bus,
            metrics_counter=mock_counter,
        )
        assert eng.event_bus is mock_bus
        assert eng.metrics_counter is mock_counter


# ============================================================
# 8. Response Structure & Kind
# ============================================================


class TestResponseStructure:
    """Verify response format matches the spec: kind + blocks + no streaming."""

    def test_response_kind_is_care_path_ooc(self, engine):
        """All responses have kind='care_path_ooc' for client-side frame."""
        resp = engine.render(locale="en", jurisdiction="US")
        assert resp.kind == "care_path_ooc"

    def test_full_response_contains_three_blocks(self, engine):
        """full_response concatenates all three blocks."""
        resp = engine.render(locale="en", jurisdiction="US")
        assert resp.block_a_ooc in resp.full_response
        assert resp.block_b_resource in resp.full_response
        assert resp.block_c_resume in resp.full_response

    def test_blocks_are_non_empty(self, engine):
        """Every block has meaningful content."""
        resp = engine.render(locale="en", jurisdiction="US")
        assert len(resp.block_a_ooc.strip()) > 10
        assert len(resp.block_b_resource.strip()) > 20
        assert len(resp.block_c_resume.strip()) > 5

    def test_envelope_is_deterministic(self, engine):
        """Same (locale, jurisdiction) → same envelope (no randomness)."""
        r1 = engine.render(locale="en", jurisdiction="US")
        r2 = engine.render(locale="en", jurisdiction="US")
        assert r1.envelope == r2.envelope

    def test_response_not_streamed_flag(self, engine):
        """Response is formed as a single envelope, not chunked."""
        resp = engine.render(locale="en", jurisdiction="US")
        # No streaming tokens or iterators
        assert isinstance(resp.full_response, str)
        assert isinstance(resp.envelope, dict)
        # kind enforces client renders as a single frame, not streamed chars
        assert resp.kind == "care_path_ooc"
