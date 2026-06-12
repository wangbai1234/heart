"""Voice subsystem exceptions — per runtime_specs/08_voice.md"""


class TTSProviderError(Exception):
    """Base exception for TTS provider errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TTSBudgetExceededError(Exception):
    """Raised when TTS budget is exceeded."""

    pass
