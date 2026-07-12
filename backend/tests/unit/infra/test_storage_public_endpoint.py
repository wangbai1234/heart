"""``is_s3_endpoint_public`` — reachability check for MiniMax voice clone.

Voice clone hands MiniMax a URL its servers must be able to fetch. Dev
setups with MinIO on ``http://localhost:9000`` used to pass ``is_s3_configured``
and then silently break the clone job when MiniMax couldn't reach the audio,
surfacing as "克隆失败" ~4s after upload with no useful reason. See
``backend/heart/infra/storage.py``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from heart.infra.storage import is_s3_endpoint_public


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:9000",
        "https://127.0.0.1:9000",
        "http://0.0.0.0:9000",
        "http://[::1]:9000",
        "http://10.0.0.5:9000",
        "http://192.168.1.10:9000",
        "http://172.16.0.4:9000",
        "http://172.20.5.5:9000",
        "http://172.31.99.99:9000",
        "http://minio.local:9000",
    ],
)
def test_private_endpoints_are_rejected(endpoint):
    with (
        patch("heart.core.config.settings.s3_endpoint_url", endpoint),
        patch("heart.core.config.settings.s3_access_key_id", "k"),
        patch("heart.core.config.settings.s3_secret_access_key", "s"),
    ):
        assert is_s3_endpoint_public() is False


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://s3.amazonaws.com",
        "https://cdn.yuoyuo.app",
        "https://storage.googleapis.com",
        # 172.15/172.32 are outside the RFC1918 172.16-172.31 range, so they're
        # public. Guard against a broken range check that greedy-matched "172.*".
        "http://172.15.0.1",
        "http://172.32.0.1",
    ],
)
def test_public_endpoints_are_accepted(endpoint):
    with (
        patch("heart.core.config.settings.s3_endpoint_url", endpoint),
        patch("heart.core.config.settings.s3_access_key_id", "k"),
        patch("heart.core.config.settings.s3_secret_access_key", "s"),
    ):
        assert is_s3_endpoint_public() is True


def test_unset_s3_returns_false():
    with (
        patch("heart.core.config.settings.s3_endpoint_url", ""),
        patch("heart.core.config.settings.s3_access_key_id", ""),
    ):
        assert is_s3_endpoint_public() is False


def test_malformed_url_does_not_crash():
    with (
        patch("heart.core.config.settings.s3_endpoint_url", "not-a-url"),
        patch("heart.core.config.settings.s3_access_key_id", "k"),
    ):
        # urlparse tolerates "not-a-url" (hostname=None), which our guard
        # treats as non-public. Guard must not raise.
        assert is_s3_endpoint_public() is False
