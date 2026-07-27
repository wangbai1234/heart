"""Regression tests for password hashing (routes_auth._hash_password/_verify_password).

Guards the passlib/bcrypt compatibility trap: passlib 1.7.4 breaks against
bcrypt >= 4.1 (reads bcrypt.__about__.__version__, removed in 4.1) and raises
ValueError inside its detect_wrap_bug self-check on bcrypt 5.x — which surfaced
in prod as a 500 ("服务器开小差了") on every /password/set and /password/change.

These tests exercise the REAL passlib CryptContext (no mocking), so an
incompatible bcrypt version fails CI here instead of in production.
"""

from heart.api.routes_auth import _hash_password, _verify_password


def test_hash_and_verify_roundtrip() -> None:
    pwd = "correct horse battery"
    hashed = _hash_password(pwd)
    assert hashed != pwd
    assert hashed.startswith("$2")  # bcrypt identifier
    assert _verify_password(pwd, hashed) is True


def test_verify_rejects_wrong_password() -> None:
    hashed = _hash_password("the-right-one-123")
    assert _verify_password("the-wrong-one-123", hashed) is False


def test_hash_is_salted_unique() -> None:
    # Same input, two hashes → different (random salt), both verify.
    h1 = _hash_password("same-password-8")
    h2 = _hash_password("same-password-8")
    assert h1 != h2
    assert _verify_password("same-password-8", h1)
    assert _verify_password("same-password-8", h2)


def test_hash_handles_unicode() -> None:
    # Chinese users: password may contain multibyte characters.
    pwd = "密码测试密码测试"
    assert _verify_password(pwd, _hash_password(pwd)) is True
