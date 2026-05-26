"""
Heart Demo CLI — entry point.

Usage:
    python -m heart.demo_cli --character rin
    python -m heart.demo_cli --character dorothy --dev --api-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Optional

from . import renderer as r
from .commands import is_command, dispatch
from .session import ClientSession

# ── prompt_toolkit (optional) ──────────────────────────────────────

try:
    from prompt_toolkit import PromptSession as PTSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.formatted_text import HTML
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


# ── Arg parsing ────────────────────────────────────────────────────


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="heart-demo",
        description="Heart 心屿 — 演示客户端",
    )
    parser.add_argument(
        "--character",
        default="rin",
        choices=["rin", "dorothy"],
        help="选择角色 (默认: rin)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Heart API 地址 (默认: http://localhost:8000)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开启 Dev 模式 (解锁 /jump, /coldwar 等)",
    )
    return parser.parse_args(argv)


# ── Prompt styling ─────────────────────────────────────────────────

def _prompt_style(character_id: str) -> str:
    """Return an HTML-styled prompt string for prompt_toolkit."""
    name_map = {"rin": "凛", "dorothy": "Dorothy"}
    display = name_map.get(character_id.lower(), character_id)
    return f"<b>{display}</b> &gt; "


def _character_color_code(character_id: str) -> str:
    """Map character to ANSI color code for prompt styling."""
    codes = {"rin": "ansipink1", "dorothy": "ansicyan1"}
    return codes.get(character_id.lower(), "")


# ── REPL loop ──────────────────────────────────────────────────────


async def repl(session: ClientSession) -> None:
    """Main REPL loop.  Reads input, dispatches to /-commands or sends to API."""

    # Build prompt_toolkit session with character-colored prompt
    if HAS_PROMPT_TOOLKIT:
        history_path = os.path.expanduser("~/.heart_demo_history")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(history_path)), exist_ok=True)
        except OSError:
            history_path = None  # fallback to in-memory

        pt = PTSession(
            history=FileHistory(history_path) if history_path else None,
            auto_suggest=AutoSuggestFromHistory(),
        )
        prompt_html = HTML(_prompt_style(session.character_id))
    else:
        pt = None
        prompt_text = f"{session.character_id}> "

    # ── Loop ───────────────────────────────────────────────────
    while True:
        try:
            if pt is not None:
                line = await pt.prompt_async(prompt_html)
            else:
                line = input(prompt_text)
        except (EOFError, KeyboardInterrupt):
            print()
            r.render_info("再见~")
            break

        line = line.strip()
        if not line:
            continue

        # ── /-command ─────────────────────────────────────────
        if is_command(line):
            result = await dispatch(session, line)
            if result.text:
                print(result.text)
            if result.exit_requested:
                break
            continue

        # ── Chat message ──────────────────────────────────────
        r.render_user_message(line, session.character_id)

        try:
            response = await session.send_message(line)
        except Exception as exc:
            r.render_error(f"发送消息失败: {exc}")
            r.render_warning(
                "请确认 API 已启动 (make up 或 make dev)。"
            )
            continue

        # Render response with streaming effect
        r.render_assistant_message(response, session.character_id)

        # Refresh side panel
        await session.refresh_side_panel()
        _show_side_panel(session)


def _show_side_panel(session: ClientSession) -> None:
    """Print side panel snapshot to stderr so it doesn't interleave with stdout."""
    panel = r.render_side_panel(session.side_panel)
    if panel is None:
        return
    console = r.get_console()
    if console is None:
        return
    # Print to stderr so prompt_toolkit doesn't capture it in the output
    console.print(panel, width=36)


# ── Main ───────────────────────────────────────────────────────────


async def main() -> None:
    args = parse_args()

    session = ClientSession(
        api_url=args.api_url.rstrip("/"),
        character_id=args.character,
        dev_mode=args.dev,
    )

    # ── Bootstrap ──────────────────────────────────────────────
    r.render_welcome(session.character_id, session.api_url, session.dev_mode)

    # Health check
    healthy = await session.check_health()
    if not healthy:
        r.render_error(
            f"无法连接到 Heart API ({session.api_url})。\n"
            f"请先启动后端: make up 或 make dev"
        )
        sys.exit(1)
    r.render_success(f"API 连接成功 ({session.api_url})")

    # Login
    try:
        token = await session.login()
        r.render_info(f"已登录 (token: {token[:20]}...)")
    except Exception as exc:
        r.render_warning(f"登录失败: {exc}。将以未认证模式继续。")

    # ── REPL ───────────────────────────────────────────────────
    try:
        await repl(session)
    except KeyboardInterrupt:
        print()
    finally:
        print()


def entry():
    """Setuptools entry point wrapper."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
