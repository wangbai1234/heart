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
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing.pricing import llm_cost_fen, story_minute_cost_fen

from . import prompt as gm_prompt
from . import repository as repo
from .models import Run, Scenario

logger = structlog.get_logger(__name__)

# Emitted by process_turn_stream as (event_type, payload) tuples so the WS layer
# (and tests) stay transport-agnostic.
StoryEvent = tuple[str, dict[str, Any]]

# ── PR5 tuning knobs ────────────────────────────────────────────────
#
# Rolling summary: once the unsummarised tail grows past SUMMARIZE_TRIGGER
# messages, fold everything except the most recent RECENT_TURNS_WINDOW into
# run.summary and advance the seq watermark. Keeps the GM context window bounded
# on long runs (per plan: 必做非可选).
SUMMARIZE_TRIGGER = gm_prompt.RECENT_TURNS_WINDOW * 2

# Safety pre-check: block a player turn only at the highest-severity tiers
# (RED = harm to others / minor / illegal, PURPLE = self-harm crisis). Romance /
# adult content is NOT a safety category in the lexicon, so it passes untouched
# (decision 3: keep 18+ behind the age-gate, never SFW-sanitise). Kept as a
# module constant so the bar is tunable without touching the flow.
_SAFETY_BLOCK_MIN_ORDINAL = 3  # SeverityLevel.RED.ordinal

# Per-minute playtime billing (PR C2): the client sends a heartbeat every 60s
# while the player page is foregrounded. Reject a heartbeat that lands sooner
# than this since the last successful charge, so a buggy/duplicated client
# heartbeat can't bill two minutes inside one wall-clock minute.
_MIN_BILL_INTERVAL_S = 45


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
            # "重新开始": retire any prior active run of this scenario so a
            # scenario has at most one active run (its history is kept, status
            # flips to 'ended'). Resume of the prior run is offered separately.
            await repo.end_active_runs_for_scenario(session, user_id, scenario.id)
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

        # All pre-flight validation (engine / empty / run / safety / billing)
        # collapses to a single error code so the turn body stays linear.
        run, cost, err = await self._preflight(run_id, user_id, text, scenario)
        if err is not None:
            yield ("error", {"code": err, "turn_id": str(turn_id)})
            yield ("turn_end", {"turn_id": str(turn_id), "ok": False})
            return
        assert run is not None  # err is None ⇒ run loaded (narrows for type-check)

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

        # Charge the LLM turn cost (idempotent; no-op for free models like
        # DeepSeek). Billing failures never lose the already-generated turn.
        if cost > 0:
            await self._charge_turn(user_id, turn_id, cost, run.model or "deepseek")

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

        # Fold older turns into the rolling summary *after* turn_end is emitted,
        # so summarisation latency never delays the player's response. Self-
        # contained error handling — a summary miss must never break the run.
        await self._maybe_summarize(run_id, user_id, scenario)

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

    # ── turn pre-flight (PR5) ────────────────────────────────────────

    async def _preflight(
        self, run_id: UUID, user_id: UUID, text: str, scenario: Scenario
    ) -> tuple[Optional[Run], int, Optional[str]]:
        """Validate a turn before generation.

        Returns (run, cost, error_code). error_code is None when the turn may
        proceed; otherwise (run, cost) are unused and the caller emits the error.
        """
        if self._router is None:
            return None, 0, "engine_unavailable"
        if not text:
            return None, 0, "empty_message"

        run = await self._load_run(run_id, user_id)
        if run is None or run.status != "active":
            return None, 0, "run_not_found"

        # Highest-severity safety pre-check (block only self-harm / illegal; see
        # _SAFETY_BLOCK_MIN_ORDINAL). Romance/adult passes through.
        if await self._is_blocked(text, user_id=user_id, scenario=scenario):
            return run, 0, "safety_blocked"

        # Credit pre-check parity with chat: refuse before generating when the
        # user can't afford the LLM turn cost (DeepSeek is 0 fen → always passes).
        cost = llm_cost_fen(run.model or "deepseek")
        if cost > 0 and not await self._can_afford(user_id, cost):
            return run, cost, "insufficient_credits"

        return run, cost, None

    # ── safety pre-check (PR5) ───────────────────────────────────────

    async def _is_blocked(self, text: str, *, user_id: UUID, scenario: Scenario) -> bool:
        """Return True only for the highest-severity self-harm / illegal input.

        Lightweight net: heuristic (Layer 1) + wellbeing accumulation (Layer 3);
        the LLM layer is intentionally skipped (model_router=None) to keep it
        fast and to avoid an upstream refusing on legitimate adult roleplay.
        Fails open on classifier error (logged), never crashing a turn.
        """
        if self._safety is None:
            return False
        try:
            result = await self._safety.classify(
                text,
                user_id=user_id,
                character_id=f"story:{scenario.id}",
                model_router=None,
            )
            return result.severity.ordinal >= _SAFETY_BLOCK_MIN_ORDINAL
        except Exception:
            logger.exception("story_safety_check_failed", scenario_id=str(scenario.id))
            return False

    # ── billing (PR5, parity with chat per-turn LLM charge) ──────────

    async def _can_afford(self, user_id: UUID, cost: int) -> bool:
        """True if the user's balance covers the turn cost (fail-open on error)."""
        from heart.billing import get_balance

        try:
            async with self._session_factory() as session:
                return await get_balance(session, user_id) >= cost
        except Exception:
            logger.exception("story_balance_check_failed", user_id=str(user_id))
            return True

    async def _charge_turn(self, user_id: UUID, turn_id: UUID, cost: int, model: str) -> None:
        """Deduct the per-turn LLM cost (idempotent). Logs, never raises."""
        from heart.billing import deduct_credits

        try:
            async with self._session_factory() as session:
                await deduct_credits(
                    session,
                    user_id,
                    cost,
                    f"story_turn:{turn_id}:llm",
                    "consume_llm",
                )
                await session.commit()
        except Exception:
            logger.exception("story_charge_failed", turn_id=str(turn_id), model=model, cost=cost)

    # ── per-minute playtime billing (PR C2) ──────────────────────────

    async def charge_playtime(self, run_id: UUID, user_id: UUID) -> tuple[str, int]:
        """Charge one minute of story playtime (driven by the client heartbeat).

        Returns ``(status, balance)`` where status is one of:

        - ``"charged"`` — one minute billed; ``balance`` is the new balance.
        - ``"throttled"`` — arrived < _MIN_BILL_INTERVAL_S since the last charge;
          nothing billed, ``balance`` unused.
        - ``"insufficient"`` — balance can't cover a minute; the run should pause
          and prompt a recharge. ``balance`` is the (unchanged) current balance.
        - ``"inactive"`` — run missing / not owned / not active; ``balance`` unused.
        - ``"free"`` — per-minute price is 0 (nothing to bill); ``balance`` unused.

        Idempotent per minute via the key ``story_time:{run}:{minute}`` where
        ``minute`` is the run's ``billed_minutes`` counter (globally unique per
        run, survives disconnect/resume). A concurrent duplicate heartbeat either
        hits the ON CONFLICT no-op deduct or the guarded ``advance_billed_minute``
        no-op, so a minute is never double-charged. Unlike ``_charge_turn`` this
        deliberately propagates nothing but a status — the WS layer decides
        whether to pause the run.
        """
        from heart.billing import InsufficientCreditsError, deduct_credits

        cost = story_minute_cost_fen()
        if cost <= 0:
            return ("free", 0)

        async with self._session_factory() as session:
            row = await repo.get_run_billing(session, run_id, user_id)
            if row is None or row.status != "active":
                return ("inactive", 0)

            now = datetime.now(timezone.utc)
            last = row.last_billed_at
            if last is not None and (now - last).total_seconds() < _MIN_BILL_INTERVAL_S:
                return ("throttled", 0)

            minute = int(row.billed_minutes)
            try:
                balance = await deduct_credits(
                    session,
                    user_id,
                    cost,
                    f"story_time:{run_id}:{minute}",
                    "story_time",
                )
            except InsufficientCreditsError as e:
                # Not enough for another minute → no advance, no commit; the
                # balance is untouched. Caller pauses the run + prompts recharge,
                # and the save is preserved so play resumes after top-up.
                return ("insufficient", e.balance)

            await repo.advance_billed_minute(session, run_id, minute, now)
            await session.commit()
            return ("charged", balance)

    # ── rolling summary (PR5) ────────────────────────────────────────

    async def _maybe_summarize(self, run_id: UUID, user_id: UUID, scenario: Scenario) -> None:
        """Compress older turns into run.summary when the tail grows too long.

        Watermark semantics: run.summary_watermark is the max message seq already
        folded into summary. We fold everything except the most recent
        RECENT_TURNS_WINDOW messages (which stay in live context via
        recent_messages), so folded and live windows never overlap.
        """
        try:
            async with self._session_factory() as session:
                run = await repo.get_run(session, run_id, user_id)
                if run is None:
                    return
                pending = await repo.list_messages(
                    session, run_id, after_seq=run.summary_watermark, limit=500
                )
            if len(pending) < SUMMARIZE_TRIGGER:
                return
            to_fold = pending[: -gm_prompt.RECENT_TURNS_WINDOW]
            if not to_fold:
                return
            new_watermark = to_fold[-1].seq

            messages = gm_prompt.build_summary_messages(scenario, run.summary, to_fold)
            new_summary = (
                await self._router.call_cheap(messages, agent_name="story_summary")
            ).strip()
            if not new_summary:
                return

            async with self._session_factory() as session:
                await repo.bump_run_activity(
                    session,
                    run_id,
                    summary=new_summary,
                    summary_watermark=new_watermark,
                )
                await session.commit()
            logger.info(
                "story_summary_folded",
                run_id=str(run_id),
                folded=len(to_fold),
                watermark=new_watermark,
            )
        except Exception:
            logger.exception("story_summarize_failed", run_id=str(run_id))
