"""Email sender abstraction with SMTP implementation."""

from __future__ import annotations

from typing import Protocol

import structlog

logger = structlog.get_logger(__name__)


class EmailSender(Protocol):
    """Protocol for email sending."""

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> None:
        """Send an email."""
        ...


class SMTPEmailSender:
    """SMTP-based email sender using aiosmtplib."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.use_tls = use_tls

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> None:
        """Send email via SMTP."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_addr
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html:
            msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
            )
            logger.info("email_sent", to=to, subject=subject)
        except Exception as e:
            logger.error("email_send_failed", to=to, error=str(e))
            raise


OTP_SUBJECT = "【yuoyuo】你的登录验证码 {code}"


def render_otp_email(code: str) -> tuple[str, str]:
    """Render OTP email content.

    Returns (plain_text, html).
    """
    plain = (
        f"你好，你的 yuoyuo 登录验证码是 {code}，5 分钟内有效。\n\n"
        "如果不是你本人操作，请忽略本邮件。"
    )
    html = f"""\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; color: #333;">
  <div style="max-width: 400px; margin: 0 auto;">
    <h2 style="color: #FFB7C5; text-align: center;">yuoyuo</h2>
    <p>你好，你的登录验证码是：</p>
    <div style="text-align: center; padding: 16px; background: #f8f8f8; border-radius: 12px; margin: 16px 0;">
      <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #333;">{code}</span>
    </div>
    <p style="color: #666; font-size: 14px;">5 分钟内有效。如果不是你本人操作，请忽略本邮件。</p>
  </div>
</body>
</html>"""
    return plain, html
