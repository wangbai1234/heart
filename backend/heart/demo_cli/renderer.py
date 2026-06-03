"""
Rich-based pretty-printing renderer for the Heart demo CLI.

Renders welcome banner, chat messages, side panel, and status messages.
"""

from __future__ import annotations

from typing import Optional

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .session import SidePanelState

# ── Character color schemes ────────────────────────────────────────

CHARACTER_COLORS: dict[str, str] = {
    "rin": "pink1",
    "dorothy": "cyan1",
    "default": "white",
}


def _color_for(character_id: str) -> str:
    return CHARACTER_COLORS.get(character_id.lower(), CHARACTER_COLORS["default"])


# ── Console ────────────────────────────────────────────────────────


def get_console() -> Optional["Console"]:
    if HAS_RICH:
        return Console()
    return None


# ── Banner ─────────────────────────────────────────────────────────


def render_welcome(character_id: str, api_url: str, dev_mode: bool) -> None:
    console = get_console()
    name_map = {"rin": "神无月 凛 (Rin)", "dorothy": "Dorothy"}
    display_name = name_map.get(character_id.lower(), character_id)
    color = _color_for(character_id)
    dev_str = "开启" if dev_mode else "关闭"

    if console is None:
        print(f"  Heart Demo CLI — {display_name} @ {api_url}")
        return

    console.print(
        Panel(
            f"[bold]{display_name}[/]\n\n"
            f"API: {api_url}\n"
            f"Dev 模式: {dev_str}\n\n"
            f"输入消息开始对话，输入 /help 查看命令。",
            title="[bold]Heart 心屿 — 演示客户端[/]",
            border_style=color,
            box=box.HEAVY,
        )
    )


# ── Side panel ─────────────────────────────────────────────────────


def render_side_panel(state: SidePanelState) -> Optional["Panel"]:
    """Build a rich Panel for the side bar."""
    if not HAS_RICH:
        return None

    stars = "★" * state.current_stage_num + "☆" * (7 - state.current_stage_num)
    lines: list[str] = []
    lines.append(f"[bold]阶段:[/] {state.current_stage}  [{stars}]")
    lines.append("")
    lines.append("[bold]情绪 (VAD):[/]")
    lines.append(
        f"  效价: {state.vad_valence:+.2f}  "
        f"唤醒: {state.vad_arousal:.2f}  "
        f"支配: {state.vad_dominance:.2f}"
    )
    if state.active_emotions:
        lines.append(f"  激活情绪: {', '.join(state.active_emotions[:3])}")
    lines.append("")

    cw = "[bold red]活跃[/]" if state.cold_war_active else "[dim]未激活[/]"
    lines.append(f"[bold]冷战:[/] {cw}")

    anni = state.last_anniversary or "[dim]无[/]"
    lines.append(f"[bold]最近纪念日:[/] {anni}")

    return Panel("\n".join(lines), title="[bold]状态面板[/]", border_style="yellow", width=36)


# ── Chat messages ──────────────────────────────────────────────────


def render_user_message(text: str, character_id: str) -> None:
    console = get_console()
    color = _color_for(character_id)
    if console is None:
        print(f"[You] {text}")
        return
    console.print(Panel(text, title="[bold]你[/]", border_style=color, box=box.ROUNDED))


def render_assistant_message(text: str, character_id: str) -> None:
    console = get_console()
    color = _color_for(character_id)
    name_map = {"rin": "凛", "dorothy": "Dorothy"}
    display_name = name_map.get(character_id.lower(), character_id)

    if console is None:
        print(f"[{character_id}] {text}")
        return

    console.print(
        Panel(text, title=f"[bold]{display_name}[/]", border_style=color, box=box.ROUNDED)
    )


# ── Streaming ──────────────────────────────────────────────────────


def render_streaming_header(character_id: str) -> Optional[str]:
    """Return character display name for streaming prefix."""
    name_map = {"rin": "凛", "dorothy": "Dorothy"}
    return name_map.get(character_id.lower(), character_id)


def render_streaming_chunk(console: Optional["Console"], chunk: str, character_id: str) -> None:
    if console is None:
        print(chunk, end="", flush=True)
        return
    color = _color_for(character_id)
    console.print(chunk, style=color, end="")


def render_streaming_finish(console: Optional["Console"]) -> None:
    if console is None:
        print()
        return
    console.print("")


# ── Status ─────────────────────────────────────────────────────────


def render_info(text: str) -> None:
    console = get_console()
    if console is None:
        print(f"[info] {text}")
        return
    console.print(f"[dim]ⓘ[/] {text}")


def render_warning(text: str) -> None:
    console = get_console()
    if console is None:
        print(f"[warn] {text}")
        return
    console.print(f"[yellow]⚠[/] {text}")


def render_error(text: str) -> None:
    console = get_console()
    if console is None:
        print(f"[err] {text}")
        return
    console.print(f"[red]✗[/] {text}")


def render_success(text: str) -> None:
    console = get_console()
    if console is None:
        print(f"[ok] {text}")
        return
    console.print(f"[green]✓[/] {text}")
