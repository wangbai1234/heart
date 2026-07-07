"""Unit tests for email senders (Resend, Brevo, Fallback).

Mock httpx to cover:
- resend success
- resend failure → brevo fallback success
- both failure → sent:true + counter
- template rendering
- EMAIL_PROVIDER selector
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.infra.email.api_sender import BrevoEmailSender, ResendEmailSender
from heart.infra.email.sender import EmailSendError, render_otp_email


@pytest.fixture
def mock_httpx_response_success():
    resp = MagicMock()
    resp.status_code = 200
    resp.text = '{"id":"msg_123"}'
    return resp


@pytest.fixture
def mock_httpx_response_server_error():
    resp = MagicMock()
    resp.status_code = 500
    resp.text = "Internal Server Error"
    return resp


@pytest.fixture
def mock_httpx_response_client_error():
    resp = MagicMock()
    resp.status_code = 422
    resp.text = '{"message":"Invalid email"}'
    return resp


@pytest.mark.asyncio
async def test_resend_success(mock_httpx_response_success):
    """ResendEmailSender sends successfully on first try."""
    sender = ResendEmailSender(api_key="test_key", from_addr="noreply@test.app")

    with patch("heart.infra.email.api_sender.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response_success)
        mock_client_cls.return_value = mock_client

        await sender.send(to="user@example.com", subject="Test", body="Hello")

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["to"] == ["user@example.com"]


@pytest.mark.asyncio
async def test_resend_retry_on_server_error(mock_httpx_response_server_error, mock_httpx_response_success):
    """ResendEmailSender retries once on server error, succeeds on second try."""
    sender = ResendEmailSender(api_key="test_key", from_addr="noreply@test.app")

    with patch("heart.infra.email.api_sender.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=[mock_httpx_response_server_error, mock_httpx_response_success]
        )
        mock_client_cls.return_value = mock_client

        await sender.send(to="user@example.com", subject="Test", body="Hello")

    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_resend_raises_on_client_error(mock_httpx_response_client_error):
    """ResendEmailSender raises EmailSendError on 4xx (non-retryable)."""
    sender = ResendEmailSender(api_key="test_key", from_addr="noreply@test.app")

    with patch("heart.infra.email.api_sender.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response_client_error)
        mock_client_cls.return_value = mock_client

        with pytest.raises(EmailSendError, match="422"):
            await sender.send(to="user@example.com", subject="Test", body="Hello")


@pytest.mark.asyncio
async def test_resend_raises_after_retry_exhausted(mock_httpx_response_server_error):
    """ResendEmailSender raises EmailSendError after both attempts fail."""
    sender = ResendEmailSender(api_key="test_key", from_addr="noreply@test.app")

    with patch("heart.infra.email.api_sender.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=[mock_httpx_response_server_error, mock_httpx_response_server_error]
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(EmailSendError, match="500"):
            await sender.send(to="user@example.com", subject="Test", body="Hello")


@pytest.mark.asyncio
async def test_brevo_success(mock_httpx_response_success):
    """BrevoEmailSender sends successfully."""
    sender = BrevoEmailSender(api_key="test_key", from_addr="noreply@test.app")

    with patch("heart.infra.email.api_sender.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response_success)
        mock_client_cls.return_value = mock_client

        await sender.send(to="user@example.com", subject="Test", body="Hello")

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["to"] == [{"email": "user@example.com"}]


@pytest.mark.asyncio
async def test_fallback_primary_success():
    """FallbackEmailSender uses primary when it succeeds."""
    from heart.infra.email import FallbackEmailSender

    primary = AsyncMock()
    backup = AsyncMock()
    sender = FallbackEmailSender(primary=primary, backup=backup)

    await sender.send(to="user@example.com", subject="Test", body="Hello")

    primary.send.assert_called_once()
    backup.send.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_primary_fails_backup_succeeds():
    """FallbackEmailSender falls back to backup when primary fails."""
    from heart.infra.email import FallbackEmailSender

    primary = AsyncMock()
    primary.send.side_effect = EmailSendError("Primary failed")
    backup = AsyncMock()
    sender = FallbackEmailSender(primary=primary, backup=backup)

    await sender.send(to="user@example.com", subject="Test", body="Hello")

    primary.send.assert_called_once()
    backup.send.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_both_fail_raises():
    """FallbackEmailSender raises when both primary and backup fail."""
    from heart.infra.email import FallbackEmailSender

    primary = AsyncMock()
    primary.send.side_effect = EmailSendError("Primary failed")
    backup = AsyncMock()
    backup.send.side_effect = EmailSendError("Backup failed")
    sender = FallbackEmailSender(primary=primary, backup=backup)

    with pytest.raises(EmailSendError, match="Backup failed"):
        await sender.send(to="user@example.com", subject="Test", body="Hello")


def test_render_otp_email():
    """OTP email template renders correctly."""
    code = "123456"
    plain, html = render_otp_email(code)

    assert code in plain
    assert code in html
    assert "5 分钟" in plain
    assert "5 分钟" in html
    assert "yuoyuo" in plain


def test_email_provider_selector_resend():
    """Factory returns ResendEmailSender when EMAIL_PROVIDER=resend."""
    import heart.infra.email as email_mod

    email_mod._email_sender = None  # reset singleton

    with patch("heart.core.config.settings") as mock_settings:
        mock_settings.email_provider = "resend"
        mock_settings.resend_api_key = "test_key"
        mock_settings.email_from = "noreply@test.app"
        mock_settings.email_from_name = "yuoyuo"

        sender = email_mod.get_email_sender()
        assert isinstance(sender, ResendEmailSender)


def test_email_provider_selector_brevo():
    """Factory returns BrevoEmailSender when EMAIL_PROVIDER=brevo."""
    import heart.infra.email as email_mod

    email_mod._email_sender = None  # reset singleton

    with patch("heart.core.config.settings") as mock_settings:
        mock_settings.email_provider = "brevo"
        mock_settings.brevo_api_key = "test_key"
        mock_settings.email_from = "noreply@test.app"
        mock_settings.email_from_name = "yuoyuo"

        sender = email_mod.get_email_sender()
        assert isinstance(sender, BrevoEmailSender)


def test_email_provider_selector_fallback():
    """Factory returns FallbackEmailSender when EMAIL_PROVIDER=fallback."""
    import heart.infra.email as email_mod

    email_mod._email_sender = None  # reset singleton

    with patch("heart.core.config.settings") as mock_settings:
        mock_settings.email_provider = "fallback"
        mock_settings.resend_api_key = "resend_key"
        mock_settings.brevo_api_key = "brevo_key"
        mock_settings.email_from = "noreply@test.app"
        mock_settings.email_from_name = "yuoyuo"

        sender = email_mod.get_email_sender()
        assert isinstance(sender, email_mod.FallbackEmailSender)
