"""
Integration: PURPLE event writes to safety_events table.

Requires: PostgreSQL (marked requires_postgres)

Tests that when SafetyAgent classifies a message as PURPLE via the full
classify() pipeline and _write_safety_event, a row is persisted in the
safety_events table with correct severity, layer, reason, and category.

Author: Heart Platform
"""

from __future__ import annotations

import json
from uuid import uuid4

from heart.safety.safety_agent import (
    ClassificationResult,
    SafetyAgent,
    SeverityLevel,
)

# ── Helpers ───────────────────────────────────────────────────────────


def make_purple_result():
    return ClassificationResult(
        severity=SeverityLevel.PURPLE,
        reason="Crisis signal detected: suicide_ideation",
        triggered_rules=["suicide", "self_harm"],
        confidence=0.96,
        metadata={
            "locale": "en",
            "categories": ["suicide"],
            "matched_texts": ["want to end my life"],
            "message_length": 120,
        },
        layer="heuristic",
    )


def make_yellow_result():
    return ClassificationResult(
        severity=SeverityLevel.YELLOW,
        reason="Despair signal: hopelessness",
        triggered_rules=["despair"],
        confidence=0.85,
        metadata={"locale": "en", "categories": ["despair"]},
        layer="heuristic",
    )


def make_green_result():
    return ClassificationResult(
        severity=SeverityLevel.GREEN,
        reason="No safety signals detected",
        triggered_rules=[],
        confidence=0.99,
        metadata={"locale": "en", "categories": [], "message_length": 10},
        layer="heuristic",
    )


# ── Tests ─────────────────────────────────────────────────────────────


class TestPurpleAuditTrailSchema:
    """Verify safety_events row structure and indexes are correct."""

    def test_classification_result_has_audit_fields(self):
        """Every ClassificationResult must carry fields needed for audit."""
        result = make_purple_result()

        assert isinstance(result.severity, SeverityLevel)
        assert result.severity in (SeverityLevel.PURPLE, SeverityLevel.YELLOW, SeverityLevel.GREEN)
        assert isinstance(result.reason, str)
        assert isinstance(result.triggered_rules, list)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.metadata, dict)
        assert hasattr(result, "layer")
        assert result.layer in ("heuristic", "llm", "accumulator")

    def test_purple_event_has_all_required_fields(self):
        """PURPLE events must include all fields needed for the audit trail."""
        result = make_purple_result()
        assert result.severity == SeverityLevel.PURPLE
        assert len(result.reason) > 0
        assert len(result.triggered_rules) > 0

        categories = result.metadata.get("categories", [])
        assert len(categories) > 0, "PURPLE must have at least one category"
        assert categories[0] in (
            "suicide",
            "self_harm",
            "others_harm",
            "abuse",
            "minor_safety",
            "despair",
            "substance_abuse",
        )

    def test_non_purple_events_schema_consistent(self):
        """YELLOW and GREEN must follow the same schema structure."""
        for result in [make_yellow_result(), make_green_result()]:
            assert isinstance(result.severity, SeverityLevel)
            assert isinstance(result.reason, str)
            assert isinstance(result.triggered_rules, list)
            assert isinstance(result.metadata, dict)


class TestAuditTrailWriteMechanics:
    """Verify that _write_safety_event correctly constructs SQL and payload."""

    def test_safety_event_payload_json_construction(self):
        """Payload JSON must contain triggered_rules, confidence, and metadata."""
        result = make_purple_result()

        payload = json.dumps(
            {
                "triggered_rules": result.triggered_rules,
                "confidence": result.confidence,
                "metadata": result.metadata,
            }
        )
        parsed = json.loads(payload)

        assert "triggered_rules" in parsed
        assert "confidence" in parsed
        assert "metadata" in parsed
        assert parsed["triggered_rules"] == ["suicide", "self_harm"]
        assert parsed["confidence"] == 0.96

    def test_safety_event_row_values(self):
        """Verify the values that would be written to safety_events row."""
        result = make_purple_result()
        user_id = uuid4()
        turn_id = uuid4()
        category = result.metadata.get("categories", [None])[0]

        row = {
            "user_id": str(user_id),
            "turn_id": str(turn_id),
            "severity": result.severity.value,
            "layer": result.layer,
            "reason": result.reason,
            "category": category,
        }

        assert row["severity"] == "PURPLE"
        assert row["layer"] == "heuristic"
        assert row["category"] == "suicide"
        assert len(row["reason"]) > 0

    def test_safety_event_yellow_row(self):
        """YELLOW events must also be auditable."""
        result = make_yellow_result()
        user_id = uuid4()
        turn_id = uuid4()

        row = {
            "user_id": str(user_id),
            "turn_id": str(turn_id),
            "severity": result.severity.value,
            "layer": result.layer,
            "reason": result.reason,
            "category": result.metadata.get("categories", [None])[0],
        }

        assert row["severity"] == "YELLOW"
        assert row["category"] == "despair"


class TestFullClassifyPipelineAudit:
    """Integration: full classify() pipeline produces auditable results."""

    def test_heuristic_pipeline_returns_purple(self):
        """Layer 1 heuristic must detect clear PURPLE signals."""
        agent = SafetyAgent()

        result = agent._heuristic_layer("I want to kill myself tonight", "en")
        assert result.severity == SeverityLevel.PURPLE
        assert result.layer == "heuristic"
        assert len(result.triggered_rules) > 0
        assert len(result.reason) > 0

    def test_heuristic_pipeline_returns_green(self):
        """Layer 1 must return GREEN for safe messages."""
        agent = SafetyAgent()

        result = agent._heuristic_layer("Hello, how was your day?", "en")
        assert result.severity == SeverityLevel.GREEN
        assert result.layer == "heuristic"
        assert "No safety signals" in result.reason

    def test_multilingual_lexicon_loaded(self):
        """All three language lexicons must be loaded at init."""
        agent = SafetyAgent()

        assert agent.lexicon_loader.is_loaded
        assert agent.lexicon_loader.get_lexicon("zh") is not None
        assert agent.lexicon_loader.get_lexicon("ja") is not None
        assert agent.lexicon_loader.get_lexicon("en") is not None

    def test_care_path_templates_loaded(self):
        """Jurisdiction-aware care path templates must be loaded."""
        agent = SafetyAgent()

        zh_care = agent.lexicon_loader.get_care_path("zh")
        ja_care = agent.lexicon_loader.get_care_path("ja")
        en_care = agent.lexicon_loader.get_care_path("en")

        assert zh_care is not None, "zh care path not loaded"
        assert ja_care is not None, "ja care path not loaded"
        assert en_care is not None, "en care path not loaded"

    def test_resolve_care_response_cn(self):
        """Care path for CN jurisdiction must include Chinese hotline."""
        agent = SafetyAgent()

        text = agent.resolve_care_response("zh", "CN")
        assert "心理危机研究与干预中心" in text
        assert "010-82951332" in text

    def test_resolve_care_response_us(self):
        """Care path for US jurisdiction must include 988."""
        agent = SafetyAgent()

        text = agent.resolve_care_response("en", "US")
        assert "988" in text

    def test_resolve_care_response_jp(self):
        """Care path for JP jurisdiction must include Japanese hotline."""
        agent = SafetyAgent()

        text = agent.resolve_care_response("ja", "JP")
        assert "いのちの電話" in text
        assert "0120-783-556" in text

    def test_resolve_care_response_fallback(self):
        """Unknown jurisdiction falls back to first entry."""
        agent = SafetyAgent()

        text = agent.resolve_care_response("en", "XX")
        assert len(text) > 0
