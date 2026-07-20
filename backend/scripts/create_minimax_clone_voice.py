"""Create a MiniMax cloned voice from a local reference audio file.

Usage:
  cd backend
  python3.11 scripts/create_minimax_clone_voice.py --write-env
"""

from __future__ import annotations

import argparse
import json
import os
import re
import wave
from pathlib import Path

import httpx

from heart.core.config import settings

DEFAULT_SOURCE = Path("assets/reference_voices/rin.mp3")
DEFAULT_PROMPT_SECONDS = 7.5
DEFAULT_DEMO_TEXT = "(breath)别担心，我会认真听你说。如果你现在有一点累，我们就慢一点，好吗？"


def _trim_wav(source: Path, seconds: float) -> Path:
    target = source.with_name(f"{source.stem}_prompt.wav")
    with wave.open(str(source), "rb") as src:
        params = src.getparams()
        frame_rate = src.getframerate()
        max_frames = int(frame_rate * seconds)
        frames = src.readframes(max_frames)

    with wave.open(str(target), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(frames)

    return target


_MIME_BY_SUFFIX = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
}


def _upload_file(client: httpx.Client, path: Path, purpose: str) -> int:
    mime = _MIME_BY_SUFFIX.get(path.suffix.lower(), "audio/wav")
    with path.open("rb") as fh:
        response = client.post(
            f"{settings.minimax_base_url}/files/upload",
            data={"purpose": purpose},
            files={"file": (path.name, fh, mime)},
        )
    response.raise_for_status()
    payload = response.json()
    return int(payload["file"]["file_id"])


def _write_env(character: str, voice_id: str) -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    key = "VOICE_PROFILES"
    content = env_path.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(key)}=.*$"
    profiles: dict[str, object] = {}
    match = re.search(pattern, content, flags=re.MULTILINE)
    if match:
        raw = match.group(0).split("=", 1)[1].strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                profiles = parsed
        except json.JSONDecodeError:
            profiles = {}

    profiles[character] = {
        "voice_id": voice_id,
        "clone_stability": True,
        "allowed_emotions": ["neutral"],
        "speed_range": [0.98, 1.02],
        "pitch_range": [-1, 0],
        "max_cues": 1,
    }
    replacement = f"{key}={json.dumps(profiles, ensure_ascii=False, separators=(',', ':'))}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}\n"
    env_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", default="rin")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--voice-id", default="")
    parser.add_argument("--prompt-audio", default="")
    parser.add_argument("--prompt-text", default="")
    parser.add_argument("--demo-text", default=DEFAULT_DEMO_TEXT)
    parser.add_argument("--text-validation", default="")
    parser.add_argument("--write-env", action="store_true")
    args = parser.parse_args()

    if not settings.minimax_api_key:
        raise SystemExit("MINIMAX_API_KEY 未配置")

    source = Path(args.source)
    if not source.is_absolute():
        source = Path(__file__).resolve().parents[1] / source
    if not source.exists():
        raise SystemExit(f"找不到参考音频: {source}")

    default_prefix = args.character[:1].upper() + args.character[1:] + "Clone"
    custom_voice_id = args.voice_id or f"{default_prefix}_{source.stat().st_mtime_ns}"

    headers = {
        "Authorization": f"Bearer {settings.minimax_api_key}",
    }
    with httpx.Client(headers=headers, timeout=120.0) as client:
        clone_file_id = _upload_file(client, source, "voice_clone")
        prompt_file_id = None
        if args.prompt_text:
            prompt_audio = (
                Path(args.prompt_audio)
                if args.prompt_audio
                else _trim_wav(source, DEFAULT_PROMPT_SECONDS)
            )
            if not prompt_audio.is_absolute():
                prompt_audio = Path(__file__).resolve().parents[1] / prompt_audio
            prompt_file_id = _upload_file(client, prompt_audio, "prompt_audio")

        payload = {
            "file_id": clone_file_id,
            "voice_id": custom_voice_id,
            "text": args.demo_text,
            "model": settings.minimax_tts_model,
            "accuracy": 0.7,
            "need_noise_reduction": False,
            "need_volume_normalization": False,
            "aigc_watermark": False,
        }
        if prompt_file_id is not None:
            payload["clone_prompt"] = {
                "prompt_audio": prompt_file_id,
                "prompt_text": args.prompt_text,
            }
        if args.text_validation:
            payload["text_validation"] = args.text_validation

        response = client.post(
            f"{settings.minimax_base_url}/voice_clone",
            headers={"Content-Type": "application/json", **headers},
            json=payload,
        )
        response.raise_for_status()
        payload = response.json()

    if args.write_env:
        _write_env(args.character, custom_voice_id)

    print(
        json.dumps(
            {
                "voice_id": custom_voice_id,
                "clone_file_id": clone_file_id,
                "prompt_file_id": prompt_file_id,
                "response": payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
