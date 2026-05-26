"""/-command dispatcher for the Heart demo CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import renderer as r
from .session import ClientSession

# ── Result type ────────────────────────────────────────────────────


@dataclass
class CommandResult:
    text: str = ""
    exit_requested: bool = False


CmdHandler = Callable[..., CommandResult]

# ── Registry ───────────────────────────────────────────────────────


_registry: dict[str, dict] = {}


def _reg(cmd: str, help_text: str, *, dev_only: bool = False):
    def deco(fn: CmdHandler):
        _registry[cmd] = {"handler": fn, "help": help_text, "dev_only": dev_only}
        return fn
    return deco


# ── Handlers ───────────────────────────────────────────────────────


@_reg("/quit", "退出程序")
def _quit(session: ClientSession, _args: list[str]) -> CommandResult:
    return CommandResult(text="再见~", exit_requested=True)


@_reg("/history", "显示最近 10 轮对话")
def _history(session: ClientSession, _args: list[str]) -> CommandResult:
    if not session.messages:
        return CommandResult(text="还没有对话历史。")

    last_n = session.messages[-20:]
    turn_start = max(1, (len(session.messages) - len(last_n)) // 2 + 1)
    lines: list[str] = []

    for i, msg in enumerate(last_n):
        role = "[你]" if msg["role"] == "user" else f"[{session.character_id}]"
        content = msg["content"]
        if len(content) > 80:
            content = content[:77] + "..."
        t = turn_start + i // 2
        lines.append(f"  {t:>3}. {role} {content}")

    return CommandResult(text="\n".join(lines))


@_reg("/state", "显示当前状态 (阶段、情绪、冷战)")
def _state(session: ClientSession, _args: list[str]) -> CommandResult:
    sp = session.side_panel
    lines = [
        f"  阶段: {sp.current_stage} ({sp.current_stage_num}/7)",
        f"  VAD: V={sp.vad_valence:+.2f} A={sp.vad_arousal:.2f} D={sp.vad_dominance:.2f}",
        f"  冷战: {'活跃' if sp.cold_war_active else '未激活'}",
    ]
    if sp.active_emotions:
        lines.append(f"  激活情绪: {', '.join(sp.active_emotions)}")
    if sp.last_anniversary:
        lines.append(f"  最近纪念日: {sp.last_anniversary}")
    return CommandResult(text="\n".join(lines))


async def _jump_impl(session: ClientSession, args: list[str]) -> CommandResult:
    """Separate async impl so decorator isn't wrapped."""
    if not args:
        return CommandResult(text="用法: /jump <1-7 | stranger | friend | ...>")
    text = await session.dev_jump_stage(args[0])
    return CommandResult(text=text)


@_reg("/jump", "<stage>  跳过至指定阶段 (需 --dev)", dev_only=True)
def _jump(session: ClientSession, args: list[str]) -> CommandResult:
    return CommandResult(text="见异步实现。")


async def _sleep_impl(session: ClientSession, _args: list[str]) -> CommandResult:
    return CommandResult(
        text="时间已快进 24 小时。\n"
             "(衰减和 inner loop 将在后端 API 就绪后触发。)"
    )


@_reg("/sleep", "快进时间 24 小时 (触发衰减 + inner loop)")
def _sleep(session: ClientSession, args: list[str]) -> CommandResult:
    return CommandResult(text="见异步实现。")


async def _coldwar_impl(session: ClientSession, args: list[str]) -> CommandResult:
    if not args or args[0].lower() != "trigger":
        return CommandResult(text="用法: /coldwar trigger")
    text = session.dev_toggle_cold_war()
    return CommandResult(text=text)


@_reg("/coldwar", "trigger  强制切换冷战状态 (需 --dev)", dev_only=True)
def _coldwar(session: ClientSession, args: list[str]) -> CommandResult:
    return CommandResult(text="见异步实现。")


@_reg("/help", "显示所有可用命令")
def _help(session: ClientSession, _args: list[str]) -> CommandResult:
    lines: list[str] = []
    for cmd, entry in sorted(_registry.items()):
        dev = " [DEV]" if entry["dev_only"] else ""
        lines.append(f"  {cmd:14s} {entry['help']}{dev}")
    lines.append("")
    lines.append("Dev 模式命令仅在 --dev 下可用。")
    return CommandResult(text="\n".join(lines))


# ── Dispatcher ─────────────────────────────────────────────────────


def is_command(text: str) -> bool:
    return text.strip().startswith("/")


async def dispatch(session: ClientSession, text: str) -> CommandResult:
    text = text.strip()
    parts = text.split(maxsplit=1)
    cmd = parts[0]
    raw = parts[1] if len(parts) > 1 else ""
    args = raw.split() if raw else []

    entry = _registry.get(cmd)
    if entry is None:
        return CommandResult(text=f"未知命令: {cmd}。输入 /help 查看可用命令。")

    if entry["dev_only"] and not session.dev_mode:
        return CommandResult(text=f"{cmd} 仅在 --dev 模式下可用。")

    # Dispatch — handle async implementations
    if cmd == "/jump":
        return await _jump_impl(session, args)
    elif cmd == "/sleep":
        return await _sleep_impl(session, args)
    elif cmd == "/coldwar":
        return await _coldwar_impl(session, args)
    else:
        result = entry["handler"](session, args)
        if hasattr(result, "__await__"):
            result = await result
        return result
