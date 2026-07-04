"""参考音频加载器单元测试。"""

import tempfile
from pathlib import Path

import pytest

from heart.ss08_voice.reference_audio import load_reference_audio


class TestLoadReferenceAudio:
    """测试 load_reference_audio 函数。"""

    def test_load_wav_file(self, tmp_path: Path):
        """测试正常加载 WAV 文件。"""
        # 创建一个小的 WAV 文件（模拟）
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"RIFF" + b"\x00" * 100)  # 简单的 WAV 头部

        result = load_reference_audio(str(wav_file))

        assert result.startswith("data:audio/wav;base64,")
        assert len(result) > 22  # 至少包含 "data:audio/wav;base64,"

    def test_load_mp3_file(self, tmp_path: Path):
        """测试正常加载 MP3 文件。"""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)  # 简单的 MP3 头部

        result = load_reference_audio(str(mp3_file))

        assert result.startswith("data:audio/mpeg;base64,")
        assert len(result) > 23  # 至少包含 "data:audio/mpeg;base64,"

    def test_file_not_found(self):
        """测试文件不存在时抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="参考音频文件不存在"):
            load_reference_audio("/nonexistent/path/audio.wav")

    def test_file_too_large(self, tmp_path: Path):
        """测试文件过大时抛出 ValueError。"""
        large_file = tmp_path / "large.wav"
        # 创建一个大于 10MB 的文件
        large_file.write_bytes(b"RIFF" + b"\x00" * (11 * 1024 * 1024))

        with pytest.raises(ValueError, match="参考音频文件过大"):
            load_reference_audio(str(large_file))

    def test_unsupported_format(self, tmp_path: Path):
        """测试不支持的格式时抛出 ValueError。"""
        unsupported_file = tmp_path / "audio.ogg"
        unsupported_file.write_bytes(b"OggS" + b"\x00" * 100)

        with pytest.raises(ValueError, match="不支持的音频格式"):
            load_reference_audio(str(unsupported_file))

    def test_data_uri_prefix(self, tmp_path: Path):
        """测试 data URI 前缀正确性。"""
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"RIFF" + b"\x00" * 50)

        result = load_reference_audio(str(wav_file))

        # 验证格式：data:<mime>;base64,<data>
        assert result.startswith("data:")
        assert ";base64," in result

        # 验证 base64 部分有效
        import base64

        _, b64_data = result.split(",", 1)
        decoded = base64.b64decode(b64_data)
        assert decoded == wav_file.read_bytes()

    def test_relative_path_resolution(self, tmp_path: Path):
        """测试相对路径解析（相对于 backend/ 目录）。"""
        # 这个测试需要模拟相对路径解析
        # 由于实际解析依赖于项目结构，这里只测试绝对路径
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"RIFF" + b"\x00" * 50)

        result = load_reference_audio(str(wav_file))
        assert result.startswith("data:audio/wav;base64,")
