"""Unit tests for the preset-sample PCM16→WAV wrapper (issue 2 preview).

MiMo returns headerless PCM16 @ 24 kHz mono; the preset preview endpoint wraps
it into a WAV container so browsers can play it from an <audio> element.
"""

from __future__ import annotations

import struct

from heart.api.routes_voice import _pcm16_to_wav


def _parse_wav_header(wav: bytes) -> dict:
    assert wav[0:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert wav[12:16] == b"fmt "
    (fmt_size, audio_format, channels, sample_rate, byte_rate, block_align, bits) = struct.unpack(
        "<IHHIIHH", wav[16:36]
    )
    assert wav[36:40] == b"data"
    (data_size,) = struct.unpack("<I", wav[40:44])
    return {
        "fmt_size": fmt_size,
        "audio_format": audio_format,
        "channels": channels,
        "sample_rate": sample_rate,
        "byte_rate": byte_rate,
        "block_align": block_align,
        "bits": bits,
        "data_size": data_size,
    }


def test_wav_header_fields_default_24k_mono():
    pcm = b"\x00\x01" * 1000  # 2000 bytes of fake PCM16
    wav = _pcm16_to_wav(pcm)
    h = _parse_wav_header(wav)
    assert h["audio_format"] == 1  # PCM
    assert h["channels"] == 1
    assert h["sample_rate"] == 24000
    assert h["bits"] == 16
    assert h["block_align"] == 2
    assert h["byte_rate"] == 24000 * 2
    assert h["data_size"] == len(pcm)


def test_wav_appends_pcm_payload_after_44_byte_header():
    pcm = b"\xab\xcd" * 500
    wav = _pcm16_to_wav(pcm)
    assert len(wav) == 44 + len(pcm)
    assert wav[44:] == pcm


def test_riff_chunk_size_is_payload_plus_36():
    pcm = b"\x10\x20" * 123
    wav = _pcm16_to_wav(pcm)
    (riff_size,) = struct.unpack("<I", wav[4:8])
    assert riff_size == 36 + len(pcm)


def test_empty_pcm_produces_valid_header():
    wav = _pcm16_to_wav(b"")
    h = _parse_wav_header(wav)
    assert h["data_size"] == 0
    assert len(wav) == 44
