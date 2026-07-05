"""Email sending infrastructure for Heart/yuoyuo."""

from .sender import EmailSender, SMTPEmailSender

__all__ = ["EmailSender", "SMTPEmailSender"]
