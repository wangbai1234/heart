"""Transactional email API senders (Resend, Brevo).

Replaces personal SMTP with anonymous offshore transactional APIs.
See docs/upgrade/commercial/06_anonymous_email_delivery.md for rationale.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from .sender import EmailSendError

logger = structlog.get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

DEFAULT_TIMEOUT = 10.0  # seconds


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    headers: dict,
    provider: str,
) -> None:
    """POST to email API with one retry on server/rate-limit errors."""
    for attempt in range(2):
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code < 300:
                logger.info("email_sent", provider=provider)
                return
            if resp.status_code < 500 and resp.status_code != 429:
                raise EmailSendError(f"{provider} API error {resp.status_code}: {resp.text}")
            if attempt == 0:
                logger.warning("email_retry", provider=provider, status=resp.status_code)
                continue
            raise EmailSendError(
                f"{provider} API error {resp.status_code} after retry: {resp.text}"
            )
        except httpx.TimeoutException as err:
            if attempt == 0:
                logger.warning("email_timeout_retry", provider=provider)
                continue
            raise EmailSendError(f"{provider} API timeout after retry") from err
        except EmailSendError:
            raise
        except Exception as e:
            if attempt == 0:
                logger.warning("email_retry", provider=provider, error=str(e))
                continue
            raise EmailSendError(f"{provider} API unexpected error: {e}") from e


class ResendEmailSender:
    """Email sender via Resend API (resend.com).

    Free tier: 100/day, 3k/month — no card, no KYC.
    """

    def __init__(self, api_key: str, from_addr: str, from_name: str = "yuoyuo") -> None:
        self.api_key = api_key
        self.from_addr = from_addr
        self.from_name = from_name

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> None:
        payload: dict[str, Any] = {
            "from": f"{self.from_name} <{self.from_addr}>",
            "to": [to],
            "subject": subject,
            "text": body,
        }
        if html:
            payload["html"] = html

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            await _post_with_retry(client, RESEND_API_URL, payload, headers, "resend")


class BrevoEmailSender:
    """Email sender via Brevo (Sendinblue) API.

    Free tier: 300/day — no card, no KYC.
    Backup provider for Resend failover.
    """

    def __init__(self, api_key: str, from_addr: str, from_name: str = "yuoyuo") -> None:
        self.api_key = api_key
        self.from_addr = from_addr
        self.from_name = from_name

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> None:
        payload: dict[str, Any] = {
            "sender": {"name": self.from_name, "email": self.from_addr},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body,
        }
        if html:
            payload["htmlContent"] = html

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            await _post_with_retry(client, BREVO_API_URL, payload, headers, "brevo")
