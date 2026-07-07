"""Email sending infrastructure for Heart/yuoyuo.

Provides:
- EmailSender Protocol
- SMTPEmailSender (legacy, local debug only)
- ResendEmailSender, BrevoEmailSender (transactional API)
- FallbackEmailSender (primary → backup failover)
- get_email_sender() factory
"""

from __future__ import annotations

import structlog

from .api_sender import BrevoEmailSender, ResendEmailSender
from .sender import EmailSender, EmailSendError, SMTPEmailSender

logger = structlog.get_logger(__name__)

__all__ = [
    "EmailSender",
    "EmailSendError",
    "SMTPEmailSender",
    "ResendEmailSender",
    "BrevoEmailSender",
    "FallbackEmailSender",
    "get_email_sender",
]


class FallbackEmailSender:
    """Composite sender: tries primary first, falls back to backup.

    Only raises if BOTH fail.
    """

    def __init__(self, primary: EmailSender, backup: EmailSender) -> None:
        self.primary = primary
        self.backup = backup

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> None:
        try:
            await self.primary.send(to, subject, body, html)
            return
        except (EmailSendError, Exception) as e:
            logger.warning(
                "email_primary_failed_fallback",
                primary=type(self.primary).__name__,
                error=str(e),
            )
        try:
            await self.backup.send(to, subject, body, html)
        except Exception as e:
            logger.error("email_all_providers_failed", error=str(e))
            raise


# ── Singleton factory ──────────────────────────────────────────────

_email_sender: EmailSender | None = None


def get_email_sender() -> EmailSender:
    """Return email sender based on EMAIL_PROVIDER setting.

    - resend: ResendEmailSender
    - brevo: BrevoEmailSender
    - smtp: SMTPEmailSender (local debug only)
    - fallback: FallbackEmailSender(ResendEmailSender, BrevoEmailSender)
    """
    from heart.core.config import settings

    global _email_sender
    if _email_sender is not None:
        return _email_sender

    provider = settings.email_provider.lower()

    if provider == "resend":
        _email_sender = ResendEmailSender(
            api_key=settings.resend_api_key,
            from_addr=settings.email_from,
            from_name=settings.email_from_name,
        )
    elif provider == "brevo":
        _email_sender = BrevoEmailSender(
            api_key=settings.brevo_api_key,
            from_addr=settings.email_from,
            from_name=settings.email_from_name,
        )
    elif provider == "smtp":
        _email_sender = SMTPEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_addr=settings.email_from,
            use_tls=settings.smtp_port == 465,
        )
    elif provider == "fallback":
        primary = ResendEmailSender(
            api_key=settings.resend_api_key,
            from_addr=settings.email_from,
            from_name=settings.email_from_name,
        )
        backup = BrevoEmailSender(
            api_key=settings.brevo_api_key,
            from_addr=settings.email_from,
            from_name=settings.email_from_name,
        )
        _email_sender = FallbackEmailSender(primary, backup)
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER: {provider!r}")

    logger.info("email_sender_initialized", provider=provider)
    return _email_sender
