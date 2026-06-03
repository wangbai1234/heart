"""replay/cli.py — Replay/debug tool CLI entry point.

Usage:
    python -m heart.replay <session_id> [--turn <n>] [--user-id <id>]

Examples:
    python -m heart.replay a1b2c3d4-e5f6-7890-abcd-ef1234567890
    python -m heart.replay a1b2c3d4-e5f6-7890-abcd-ef1234567890 --turn 5
    python -m heart.replay a1b2c3d4-e5f6-7890-abcd-ef1234567890 --user-id user_001

Privacy gate:
    - If HEART_DEV_MODE=true, all access allowed.
    - Otherwise, --user-id must match the snapshot's user_id.
"""

import argparse
import asyncio
import os
import sys
import uuid
from typing import Optional

from .bundle_dump import PromptBundle, ReplayRecorder
from .diff_view import render_diff
from .layer_view import render_layer_tree


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="heart-replay",
        description="Heart 心屿 — Conversation replay/debug tool. "
        "Inspect full prompt bundles, composer layers, anti-pattern hits, "
        "and LLM response diffs for a given session + turn.",
    )
    parser.add_argument(
        "session_id",
        help="Session UUID to replay",
    )
    parser.add_argument(
        "--turn",
        "-t",
        type=int,
        default=None,
        help="Turn number (1-indexed) within the session. If omitted, shows all turns.",
    )
    parser.add_argument(
        "--user-id",
        "-u",
        default=None,
        help="User ID for privacy gate. Required unless HEART_DEV_MODE=true.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://heart:heartdev@localhost:5432/heart"
        ),
        help="PostgreSQL connection string (default from DATABASE_URL env).",
    )
    parser.add_argument(
        "--layer-only",
        "-l",
        action="store_true",
        help="Show only the layer tree view (skip diff).",
    )
    parser.add_argument(
        "--diff-only",
        "-d",
        action="store_true",
        help="Show only the diff view (skip layers).",
    )
    return parser.parse_args(argv)


async def _check_privacy(
    recorder: ReplayRecorder,
    session_id: uuid.UUID,
    user_id: Optional[str],
    turn_n: Optional[int],
) -> Optional[str]:
    """Verify privacy gate. Returns None if access denied, or the snapshot's user_id if OK."""
    bundles = await recorder.load_by_session(session_id, turn_n)
    if not bundles:
        return None  # Let caller report "not found"

    # Dev mode bypass
    if os.getenv("HEART_DEV_MODE", "").lower() == "true":
        return bundles[0].user_id

    # Must have a user_id claim that matches
    if user_id is None:
        print(
            "⚠  Privacy gate: --user-id is required unless HEART_DEV_MODE=true.",
            file=sys.stderr,
        )
        return None

    # Check all loaded bundles match the claimed user
    for b in bundles:
        if b.user_id != user_id:
            print(
                f"⛔ Access denied: snapshot belongs to user '{b.user_id}', "
                f"but you claimed '{user_id}'.",
                file=sys.stderr,
            )
            return None

    return user_id


def _print_bundle_summary(bundles: list[PromptBundle]) -> None:
    """Print a summary table of all bundles found."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for i, b in enumerate(bundles, 1):
            print(
                f"  Turn {i}: {b.turn_id}  hits={b.anti_pattern_hits}  "
                f"latency={b.latency_ms}ms  tokens={b.token_count}"
            )
        return

    console = Console()
    table = Table(title="[bold]Replay Snapshots[/]", title_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Turn ID", style="cyan")
    table.add_column("Character", width=12)
    table.add_column("Hits", justify="center")
    table.add_column("Blocked", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Critic", justify="right")

    for i, b in enumerate(bundles, 1):
        hits_str = f"[red]{len(b.anti_pattern_hits)}[/]" if b.anti_pattern_hits else "[green]0[/]"
        blocked_str = "[red]✗[/]" if b.blocked else "[green]✓[/]"
        critic_str = f"{b.critic_score:.2f}" if b.critic_score is not None else "[dim]—[/]"
        table.add_row(
            str(i),
            str(b.turn_id)[:8] + "…",
            b.character_id,
            hits_str,
            blocked_str,
            f"{b.latency_ms}ms",
            str(b.token_count),
            critic_str,
        )

    console.print(table)


async def main(argv: Optional[list[str]] = None) -> int:  # noqa: C901
    args = _parse_args(argv)

    # Validate session_id
    try:
        session_id = uuid.UUID(args.session_id)
    except ValueError:
        print(f"Invalid session_id UUID: {args.session_id}", file=sys.stderr)
        return 1

    # Build engine and recorder
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
    except ImportError:
        print("SQLAlchemy not installed. Run: pip install sqlalchemy[asyncio]", file=sys.stderr)
        return 1

    engine = create_async_engine(args.database_url, echo=False)
    recorder = ReplayRecorder(engine)

    try:
        # Privacy gate
        authorized_user = await _check_privacy(recorder, session_id, args.user_id, args.turn)
        if authorized_user is None:
            # Check if the session exists at all
            all_bundles = await recorder.load_by_session(session_id, None)
            if not all_bundles:
                print(f"No snapshots found for session {args.session_id}", file=sys.stderr)
            return 1

        # Load bundles
        bundles = await recorder.load_by_session(session_id, args.turn)
        if not bundles:
            print(
                f"Turn {args.turn} not found for session {args.session_id} "
                f"({len(await recorder.load_by_session(session_id, None))} turns total)",
                file=sys.stderr,
            )
            return 1

        # Summary if multiple bundles
        if len(bundles) > 1:
            _print_bundle_summary(bundles)
            print()
        elif args.turn is None:
            # Show all turns individually (will print summary then stop)
            _print_bundle_summary(bundles)
            return 0

        # Render each bundle
        for bundle in bundles:
            if not args.diff_only:
                render_layer_tree(bundle)
                print()

            if not args.layer_only:
                render_diff(bundle)
                print()

        return 0

    finally:
        await engine.dispose()


def entry() -> None:
    """Setuptools entry point wrapper."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
