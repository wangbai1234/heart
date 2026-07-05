"""参考音频加载器 — 加载 WAV/MP3 文件并 base64 编码为 data URI。"""

import base64
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# 支持的音频格式和对应的 MIME 类型
_MIME_TYPES: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
}

# 最大文件大小：10MB
_MAX_FILE_SIZE = 10 * 1024 * 1024


def load_reference_audio(path: str) -> str:
    """加载参考音频文件并 base64 编码。

    Args:
        path: 音频文件路径（相对于 backend/ 目录或绝对路径）

    Returns:
        'data:audio/wav;base64,...' 或 'data:audio/mpeg;base64,...'

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件大小超过 10MB 或格式不支持
    """
    file_path = Path(path)

    # 如果是相对路径，相对于 backend/ 目录解析
    if not file_path.is_absolute():
        # 从当前文件向上找到 backend/ 目录
        backend_dir = Path(__file__).resolve().parent.parent.parent
        file_path = backend_dir / path

    # 检查文件是否存在
    if not file_path.exists():
        raise FileNotFoundError(f"参考音频文件不存在: {file_path}")

    # 获取文件后缀并检查格式
    suffix = file_path.suffix.lower()
    if suffix not in _MIME_TYPES:
        raise ValueError(f"不支持的音频格式: {suffix}。支持的格式: {list(_MIME_TYPES.keys())}")

    # 检查文件大小
    file_size = file_path.stat().st_size
    if file_size > _MAX_FILE_SIZE:
        raise ValueError(
            f"参考音频文件过大: {file_size / 1024 / 1024:.1f}MB。最大允许: {_MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )

    # 读取并 base64 编码
    audio_bytes = file_path.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    # 构造 data URI
    mime_type = _MIME_TYPES[suffix]
    data_uri = f"data:{mime_type};base64,{audio_b64}"

    logger.info(
        "参考音频加载完成",
        path=str(file_path),
        size_kb=round(file_size / 1024, 1),
        format=suffix,
    )

    return data_uri
