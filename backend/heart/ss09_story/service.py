"""StoryService — the SS09 turn engine.

Orchestrates a story run's lifecycle over the raw-SQL repository + a
ModelRouter, deliberately bypassing the persona Orchestrator (ss07). A turn is:

    player text → persist → build GM messages → stream_for() → split into
    bubbles → persist each bubble → emit frames.

Billing, the highest-severity safety pre-check, and rolling summarisation are
seams here but hardened in PR5 (see the TODO markers); PR3 delivers a minimal,
never-crashing turn stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from . import prompt as gm_prompt
from . import repository as repo
from .models import Run, Scenario

logger = structlog.get_logger(__name__)

# Emitted by process_turn_stream as (event_type, payload) tuples so the WS layer
# (and tests) stay transport-agnostic.
StoryEvent = tuple[str, dict[str, Any]]


@dataclass
class StartRunResult:
    run: Run
    opening_bubbles: list[dict[str, Any]]


class StoryEngineUnavailable(RuntimeError):
    """Raised when the LLM router isn't configured (no API key)."""


class StoryService:
    def __init__(self, session_factory: Any, model_router: Any, safety_agent: Any = None):
        self._session_factory = session_factory
        self._router = model_router
        self._safety = safety_agent

    # ── run lifecycle ────────────────────────────────────────────────

    async def start_run(
        self,
        *,
        user_id: UUID,
        scenario: Scenario,
        player_identity: dict[str, Any],
    ) -> StartRunResult:
        """Create a run and generate the opening GM turn.

        The opening isn't pre-stored on the scenario: under raw-injection the GM
        writes the opening live from the scenario prompt. Persisted as the run's
        first messages so resume replays them.
        """
        if self._router is None:
            raise StoryEngineUnavailable("model_router_unavailable")

        async with self._session_factory() as session:
            run = await repo.create_run(
                session,
                user_id=user_id,
                scenario_id=scenario.id,
                player_identity=player_identity,
                title=scenario.title,
                model="deepseek",
            )
            await session.commit()

        # Generate the opening with an empty transcript (system prompt only).
        turn_id = uuid4()
        full_text = await self._generate(scenario, run, recent_turns=[])
        bubbles = gm_prompt.split_gm_text(full_text)

        async with self._session_factory() as session:
            seq = await repo.next_seq(session, run.id)
            for b in bubbles:
                await repo.add_message(
                    session,
                    run_id=run.id,
                    user_id=user_id,
                    turn_id=turn_id,
                    seq=seq,
                    role=("npc" if b["kind"] == "dialogue" else "gm"),
                    kind=b["kind"],
                    content=b["content"],
                    npc_name=b.get("npc_name"),
                )
                seq += 1
            await repo.bump_run_activity(session, run.id, turns_delta=1)
            await session.commit()

        return StartRunResult(run=run, opening_bubbles=bubbles)

    async def process_turn_stream(
        self,
        *,
        run_id: UUID,
        user_id: UUID,
        player_text: str,
        scenario: Scenario,
        turn_id: Optional[UUID] = None,
    ) -> AsyncGenerator[StoryEvent, None]:
        """Drive one player→GM turn, yielding (event, payload) frames.

        Frames mirror the chat WS vocabulary: turn_start / text_delta /
        message_bubble / turn_end (+ error). Never raises into the caller — any
        failure surfaces as an ('error', …) frame so a run can't crash a socket.
        """
        turn_id = turn_id or uuid4()
        text = (player_text or "").strip()
        yield ("turn_start", {"turn_id": str(turn_id)})

        if self._router is None:
            yield ("error", {"code": "engine_unavailable", "turn_id": str(turn_id)})
            yield ("turn_end", {"turn_id": str(turn_id), "ok": False})
            return

        if not text:
            yield ("error", {"code": "empty_message", "turn_id": str(turn_id)})
            yield ("turn_end", {"turn_id": str(turn_id), "ok": False})
            return

        # TODO(PR5): highest-severity safety pre-check via self._safety
        # (block only self-harm / illegal categories; romance/adult pass).
        # TODO(PR5): credit debit parity with chat (deduct_credits).

        run = await self._load_run(run_id, user_id)
        if run is None or run.status != "active":
            yield ("error", {"code": "run_not_found", "turn_id": str(turn_id)})
            yield ("turn_end", {"turn_id": str(turn_id), "ok": False})
            return

        # Persist the player line first (so it survives a mid-generation crash).
        async with self._session_factory() as session:
            seq = await repo.next_seq(session, run_id)
            await repo.add_message(
                session,
                run_id=run_id,
                user_id=user_id,
                turn_id=turn_id,
                seq=seq,
                role="player",
                kind="narration",
                content=text,
            )
            await session.commit()

        # Load recent context and stream the GM response.
        async with self._session_factory() as session:
            recent = await repo.recent_messages(
                session, run_id, limit=gm_prompt.RECENT_TURNS_WINDOW
            )
        messages = gm_prompt.build_gm_messages(scenario, run, recent)

        collected: list[str] = []
        try:
            async for delta in self._router.stream_for(
                run.model or "deepseek",
                messages,
                agent_name="story_gm",
            ):
                if delta:
                    collected.append(delta)
                    yield ("text_delta", {"turn_id": str(turn_id), "delta": delta})
        except Exception:
            # Not a silent swallow: logged with stack + surfaced as a structured
            # error/partial-persist path (per CLAUDE.md DB 铁律 #5).
            logger.exception("story_turn_generation_failed", run_id=str(run_id))
            if not collected:
                yield ("error", {"code": "generation_failed", "turn_id": str(turn_id)})
                yield ("turn_end", {"turn_id": str(turn_id), "ok": False})
                return
            # Partial content already streamed — fall through and persist it.

        full_text = "".join(collected)
        bubbles = gm_prompt.split_gm_text(full_text)

        async with self._session_factory() as session:
            seq = await repo.next_seq(session, run_id)
            for b in bubbles:
                await repo.add_message(
                    session,
                    run_id=run_id,
                    user_id=user_id,
                    turn_id=turn_id,
                    seq=seq,
                    role=("npc" if b["kind"] == "dialogue" else "gm"),
                    kind=b["kind"],
                    content=b["content"],
                    npc_name=b.get("npc_name"),
                )
                seq += 1
            await repo.bump_run_activity(session, run_id, turns_delta=1)
            await session.commit()

        for b in bubbles:
            yield (
                "message_bubble",
                {
                    "turn_id": str(turn_id),
                    "kind": b["kind"],
                    "npc_name": b.get("npc_name"),
                    "content": b["content"],
                },
            )
        yield ("turn_end", {"turn_id": str(turn_id), "ok": True})

    # ── helpers ──────────────────────────────────────────────────────

    async def _load_run(self, run_id: UUID, user_id: UUID) -> Optional[Run]:
        async with self._session_factory() as session:
            return await repo.get_run(session, run_id, user_id)

    async def _generate(self, scenario: Scenario, run: Run, recent_turns: list) -> str:
        """Non-streaming full generation (used for the opening turn)."""
        messages = gm_prompt.build_gm_messages(scenario, run, recent_turns)
        chunks: list[str] = []
        async for delta in self._router.stream_for(
            run.model or "deepseek", messages, agent_name="story_gm_opening"
        ):
            if delta:
                chunks.append(delta)
        return "".join(chunks)
