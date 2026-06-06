"""Safe logging utilities to avoid rich/structlog traceback formatting bugs.

Usage:
    from heart.core.safe_logger import safe_logger

    try:
        ...
    except Exception as e:
        safe_logger.error("my_event", error=str(e), extra_key="value")
"""

import structlog

logger = structlog.get_logger()


def safe_logger():
    """Return a logger that safely handles exceptions without rich traceback bug."""
    return _SafeLogger()


class _SafeLogger:
    """Wrapper around structlog that avoids rich traceback formatting issues."""

    def __getattr__(self, name: str):
        """Return safe versions of log methods."""
        if name == "exception":
            return self._safe_exception
        return getattr(logger, name)

    def _safe_exception(self, event: str, **kw):
        """Log at error level instead of exception to avoid rich traceback bug."""
        logger.error(event, **kw)
