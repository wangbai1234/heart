"""``_stage_audio_for_clone`` — S3 vs MiniMax /files/upload routing.

Regression test for 2026-07-12: dev with ``S3_ENDPOINT_URL=http://localhost:9000``
passed ``is_s3_configured`` and returned a MinIO URL that MiniMax's servers
could not reach, surfacing as "克隆失败" ~4s after upload. The staging
function now routes through MiniMax's own ``/files/upload`` when the S3
endpoint is not publicly reachable.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from heart.api import routes_voice


@pytest.mark.asyncio
async def test_stage_audio_uses_minimax_upload_when_s3_endpoint_is_private():
    """Localhost/private S3 → MiniMax /files/upload → ``minimax_file://<id>``."""
    with (
        patch("heart.infra.storage.is_s3_endpoint_public", return_value=False),
        patch.object(
            routes_voice,
            "_upload_audio_to_minimax",
            new=AsyncMock(return_value=987654321),
        ) as mock_upload,
    ):
        got = await routes_voice._stage_audio_for_clone(
            data=b"\x00" * 4096,
            filename="sample.wav",
            mime="audio/wav",
            character_id="char_xyz",
            provider="minimax",
        )
    assert got == "minimax_file://987654321"
    mock_upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_stage_audio_uses_s3_when_endpoint_is_public():
    """Public S3 (CDN / AWS) → upload once, return the reachable URL."""
    fake_url = "https://cdn.yuoyuo.app/heart/voice-samples/char_xyz/abc.wav"
    with (
        patch("heart.infra.storage.is_s3_endpoint_public", return_value=True),
        patch(
            "heart.infra.storage.upload_file",
            new=AsyncMock(return_value=fake_url),
        ) as mock_s3,
        patch.object(
            routes_voice,
            "_upload_audio_to_minimax",
            new=AsyncMock(return_value=42),
        ) as mock_minimax,
    ):
        got = await routes_voice._stage_audio_for_clone(
            data=b"\x00" * 4096,
            filename="sample.wav",
            mime="audio/wav",
            character_id="char_xyz",
            provider="minimax",
        )
    assert got == fake_url
    mock_s3.assert_awaited_once()
    mock_minimax.assert_not_called()


@pytest.mark.asyncio
async def test_stage_audio_fish_returns_upload_marker_without_touching_storage():
    """Fish clones by direct bytes upload → staging must NOT hit S3/MiniMax and
    must return a plain ``upload://`` record marker (no fetchable URL to 403 on)."""
    with (
        patch("heart.infra.storage._upload_to_s3", new=AsyncMock()) as mock_s3,
        patch.object(routes_voice, "_upload_audio_to_minimax", new=AsyncMock()) as mock_mm,
    ):
        got = await routes_voice._stage_audio_for_clone(
            data=b"\x00" * 4096,
            filename="my sample.wav",
            mime="audio/wav",
            character_id="char_xyz",
            provider="fish",
        )
    assert got == "upload://my sample.wav"
    mock_s3.assert_not_called()
    mock_mm.assert_not_called()


# NOTE: MiMo clone was retired (zero-shot quality too poor). Its staging path
# (s3:// reference handle) is gone — cloning is Fish-only now, so the former
# test_stage_audio_mimo_* cases were removed with it. Fish staging is covered by
# test_stage_audio_fish_returns_upload_marker_without_touching_storage above.
