"""Tests for JWT secret validation at Settings load time."""

import pytest

from heart.core.config import Settings


class TestJwtSecretValidation:
    """Ensure Settings raises RuntimeError for weak JWT secrets."""

    WEAK_SECRETS = [
        "your-secret-key-here",
        "change-me",
        "",
        "short",  # length < 32
    ]

    STRONG_SECRET = "a" * 32  # exactly 32 chars, passes min-length check

    def test_weak_secrets_raise_runtime_error(self):
        """All known-weak / short secrets must raise RuntimeError."""
        for weak in self.WEAK_SECRETS:
            with pytest.raises(
                RuntimeError, match="JWT_SECRET_KEY must be set to a strong random value"
            ):
                Settings(
                    jwt_secret_key=weak,
                    jwt_algorithm="HS256",
                )

    def test_strong_secret_does_not_raise(self):
        """A 32-char secret should pass validation."""
        try:
            Settings(
                jwt_secret_key=self.STRONG_SECRET,
                jwt_algorithm="HS256",
            )
        except RuntimeError:
            pytest.fail("Settings raised RuntimeError for a valid-length secret")

    def test_default_secret_raises(self):
        """With no explicit secret, the default placeholder must fail (no .env override)."""
        saved = Settings.model_config.get("env_file")
        Settings.model_config["env_file"] = ".env.nonexistent"
        try:
            with pytest.raises(
                RuntimeError, match="JWT_SECRET_KEY must be set to a strong random value"
            ):
                Settings()
        finally:
            if saved is not None:
                Settings.model_config["env_file"] = saved
            else:
                Settings.model_config.pop("env_file", None)
