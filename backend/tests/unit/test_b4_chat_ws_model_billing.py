"""Unit tests for B4: chat WS per-model billing + assert_model_allowed."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _charge_llm_cost — idempotency key + skip-when-free
# ---------------------------------------------------------------------------


class TestChargeLlmCost:
    @pytest.mark.asyncio
    async def test_deepseek_returns_zero_no_deduction(self):
        from heart.api.routes_chat_ws import _charge_llm_cost

        db = AsyncMock()
        cost, bal = await _charge_llm_cost(db, uuid.uuid4(), str(uuid.uuid4()), "deepseek")
        assert cost == 0
        assert bal == 0
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_grok_deducts_with_idempotency_key(self):
        from heart.api.routes_chat_ws import _charge_llm_cost

        db = AsyncMock()
        turn_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        with patch("heart.billing.deduct_credits", new=AsyncMock(return_value=5000)) as mock_deduct:
            cost, bal = await _charge_llm_cost(db, user_id, turn_id, "grok")

        assert cost == 300  # grok_cost_credits=3 → 300 fen
        assert bal == 5000
        mock_deduct.assert_called_once_with(
            db, user_id, 300, f"turn:{turn_id}:llm", "consume_llm"
        )

    @pytest.mark.asyncio
    async def test_claude_deducts_1200_fen(self):
        from heart.api.routes_chat_ws import _charge_llm_cost

        db = AsyncMock()
        turn_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        with patch("heart.billing.deduct_credits", new=AsyncMock(return_value=3000)) as mock_deduct:
            cost, bal = await _charge_llm_cost(db, user_id, turn_id, "claude")

        assert cost == 1200  # claude_cost_credits=12 → 1200 fen
        assert bal == 3000
        mock_deduct.assert_called_once_with(
            db, user_id, 1200, f"turn:{turn_id}:llm", "consume_llm"
        )

    @pytest.mark.asyncio
    async def test_idempotency_key_format(self):
        """Key must be 'turn:<turn_id>:llm' — downstream billing relies on this."""
        from heart.api.routes_chat_ws import _charge_llm_cost

        captured = {}

        async def fake_deduct(db, user_id, amount, idempotency_key, reason):
            captured["key"] = idempotency_key
            return 0

        db = AsyncMock()
        turn_id = "abc-123-def"
        with patch("heart.billing.deduct_credits", new=fake_deduct):
            await _charge_llm_cost(db, uuid.uuid4(), turn_id, "grok")

        assert captured["key"] == "turn:abc-123-def:llm"


# ---------------------------------------------------------------------------
# _precheck_billing — model_forbidden gate
# ---------------------------------------------------------------------------


class TestPrecheckBillingModelForbidden:
    @pytest.mark.asyncio
    async def test_grok_forbidden_for_free_user(self):
        """Free tier user requesting grok should receive model_forbidden event."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        user_id = uuid.uuid4()
        turn_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        # voice_enabled query → False
        voice_result = MagicMock()
        voice_result.scalar_one_or_none.return_value = False
        # balance query → high balance
        balance_result = MagicMock()
        balance_result.scalar_one_or_none.return_value = 100000

        mock_db.execute = AsyncMock(side_effect=[voice_result, balance_result])

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch(
                "sqlalchemy.ext.asyncio.AsyncSession",
                return_value=mock_db,
            ),
        ):
            _voice, can_proceed = await _precheck_billing(
                user_id, "char1", turn_id, ws, model="grok"
            )

        assert can_proceed is False
        ws.send_json.assert_called_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "model_forbidden"
        assert sent["model"] == "grok"
        assert sent["tier"] == "free"
        assert sent["turn_id"] == turn_id

    @pytest.mark.asyncio
    async def test_deepseek_allowed_for_free_user(self):
        """Free tier user requesting deepseek should proceed."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        user_id = uuid.uuid4()
        turn_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        voice_result = MagicMock()
        voice_result.scalar_one_or_none.return_value = False
        balance_result = MagicMock()
        balance_result.scalar_one_or_none.return_value = 100000
        mock_db.execute = AsyncMock(side_effect=[voice_result, balance_result])

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_db),
        ):
            _voice, can_proceed = await _precheck_billing(
                user_id, "char1", turn_id, ws, model="deepseek"
            )

        assert can_proceed is True
        # No model_forbidden event for deepseek
        for call in ws.send_json.call_args_list:
            assert call[0][0].get("type") != "model_forbidden"


# ---------------------------------------------------------------------------
# TurnRequest carries model field
# ---------------------------------------------------------------------------


class TestTurnRequestModelField:
    def test_default_model_is_deepseek(self):
        from heart.ss07_orchestration.models import TurnRequest

        req = TurnRequest(
            user_id=uuid.uuid4(),
            character_id="rin",
            user_message="hi",
            history=[],
            trace_id=uuid.uuid4(),
        )
        assert req.model == "deepseek"

    def test_model_is_stored(self):
        from heart.ss07_orchestration.models import TurnRequest

        req = TurnRequest(
            user_id=uuid.uuid4(),
            character_id="rin",
            user_message="hi",
            history=[],
            trace_id=uuid.uuid4(),
            model="grok",
        )
        assert req.model == "grok"


# ---------------------------------------------------------------------------
# CompositionContext carries model + stream_meta
# ---------------------------------------------------------------------------


class TestCompositionContextModelFields:
    def test_default_model_is_deepseek(self):
        from heart.ss05_composer.service import CompositionContext

        ctx = CompositionContext(
            user_id=uuid.uuid4(),
            character_id="rin",
            turn_id=uuid.uuid4(),
        )
        assert ctx.model == "deepseek"
        assert ctx.stream_meta == {}

    def test_model_can_be_set(self):
        from heart.ss05_composer.service import CompositionContext

        ctx = CompositionContext(
            user_id=uuid.uuid4(),
            character_id="rin",
            turn_id=uuid.uuid4(),
            model="claude",
        )
        assert ctx.model == "claude"


# ---------------------------------------------------------------------------
# _upload_turn_audio helper
# ---------------------------------------------------------------------------


class TestUploadTurnAudio:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_audio(self):
        from heart.api.routes_chat_ws import _upload_turn_audio

        session = MagicMock()
        session.full_audio = b""
        url, dur = await _upload_turn_audio(session, uuid.uuid4(), "turn-1")
        assert url is None
        assert dur is None

    @pytest.mark.asyncio
    async def test_returns_none_when_session_is_none(self):
        from heart.api.routes_chat_ws import _upload_turn_audio

        url, dur = await _upload_turn_audio(None, uuid.uuid4(), "turn-1")
        assert url is None
        assert dur is None

    @pytest.mark.asyncio
    async def test_skips_when_s3_not_configured(self):
        from heart.api.routes_chat_ws import _upload_turn_audio

        session = MagicMock()
        session.full_audio = b"\x00" * 1000

        with patch("heart.infra.storage.is_s3_configured", return_value=False):
            url, dur = await _upload_turn_audio(session, uuid.uuid4(), "turn-1")

        assert url is None
        assert dur is None
