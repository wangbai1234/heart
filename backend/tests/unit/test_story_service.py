"""Unit tests for StoryService.process_turn_stream (PR3).

Uses a fake router (deterministic delta stream) and monkeypatched repository so
no DB is required — the focus is the event-frame contract and bubble persistence
wiring, not SQL.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from heart.ss09_story import repository as repo
from heart.ss09_story import service as service_mod
from heart.ss09_story.models import Run, Scenario
from heart.ss09_story.service import StoryService


class _FakeRouter:
    def __init__(self, deltas: list[str] | None = None, raise_after: int | None = None):
        self._deltas = deltas if deltas is not None else ["【旁白】开场。\n", "**林深** 你好。"]
        self._raise_after = raise_after
        self.cheap_calls: list[list[dict]] = []

    async def stream_for(self, model, messages, agent_name="unknown", **kw):
        for i, d in enumerate(self._deltas):
            if self._raise_after is not None and i == self._raise_after:
                raise RuntimeError("boom")
            yield d

    async def call_cheap(self, messages, agent_name="unknown", **kw):
        self.cheap_calls.append(messages)
        return "前情提要：主控推门进入。"


class _FakeSafety:
    """Minimal safety agent stub — returns a fixed severity ordinal."""

    def __init__(self, ordinal: int):
        self._ordinal = ordinal

    async def classify(self, message, **kw):
        class _Sev:
            def __init__(self, o):
                self.ordinal = o

        class _Result:
            def __init__(self, o):
                self.severity = _Sev(o)

        return _Result(self._ordinal)


class _FakeSession:
    async def commit(self):
        return None


@asynccontextmanager
async def _fake_session_ctx():
    yield _FakeSession()  # repo fns are monkeypatched; only commit() is called


def _fake_factory():
    return _fake_session_ctx()


def _scenario() -> Scenario:
    return Scenario(
        id=uuid4(), slug="s", title="t", genre="悬疑", cover_url=None, blurb="b",
        maturity="all_ages", gm_system_prompt="原文", player_template_json={},
        status="published", is_featured=False, play_count=0,
    )


def _run() -> Run:
    now = datetime.now(timezone.utc)
    return Run(
        id=uuid4(), user_id=uuid4(), scenario_id=uuid4(), player_identity_json={},
        title="t", summary="", summary_watermark=0, turn_count=0, status="active",
        model="deepseek", created_at=now, last_activity_at=now,
    )


@pytest.fixture
def patched_repo(monkeypatch):
    """Stub all repo writes/reads the service touches; record added messages."""
    added: list[dict] = []
    run = _run()

    async def _next_seq(session, run_id):
        return len(added) + 1

    async def _add_message(session, **kw):
        added.append(kw)
        return object()

    async def _bump(session, run_id, **kw):
        return None

    async def _get_run(session, run_id, user_id):
        return run

    async def _recent(session, run_id, limit=16):
        return []

    async def _list_messages(session, run_id, after_seq=0, limit=200):
        return []

    monkeypatch.setattr(repo, "next_seq", _next_seq)
    monkeypatch.setattr(repo, "add_message", _add_message)
    monkeypatch.setattr(repo, "bump_run_activity", _bump)
    monkeypatch.setattr(repo, "get_run", _get_run)
    monkeypatch.setattr(repo, "recent_messages", _recent)
    monkeypatch.setattr(repo, "list_messages", _list_messages)
    return {"added": added, "run": run}


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.mark.asyncio
async def test_turn_stream_happy_path(patched_repo):
    svc = StoryService(_fake_factory, _FakeRouter())
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="我推门进去。",
            scenario=_scenario(),
        )
    )
    types = [e[0] for e in events]
    assert types[0] == "turn_start"
    assert "text_delta" in types
    assert types[-1] == "turn_end"
    assert events[-1][1]["ok"] is True
    # message_bubble frames for narration + dialogue.
    bubbles = [e[1] for e in events if e[0] == "message_bubble"]
    kinds = [b["kind"] for b in bubbles]
    assert "narration" in kinds and "dialogue" in kinds
    # Player line + each bubble persisted.
    roles = [m["role"] for m in patched_repo["added"]]
    assert "player" in roles
    assert "npc" in roles  # dialogue bubble persisted as npc


@pytest.mark.asyncio
async def test_turn_stream_empty_text_errors(patched_repo):
    svc = StoryService(_fake_factory, _FakeRouter())
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="   ",
            scenario=_scenario(),
        )
    )
    types = [e[0] for e in events]
    assert types == ["turn_start", "error", "turn_end"]
    assert events[1][1]["code"] == "empty_message"


@pytest.mark.asyncio
async def test_turn_stream_engine_unavailable():
    svc = StoryService(_fake_factory, None)  # no router
    events = await _collect(
        svc.process_turn_stream(
            run_id=uuid4(), user_id=uuid4(), player_text="hi", scenario=_scenario()
        )
    )
    codes = [e[1].get("code") for e in events if e[0] == "error"]
    assert "engine_unavailable" in codes


@pytest.mark.asyncio
async def test_turn_stream_generation_error_before_any_delta(patched_repo):
    svc = StoryService(_fake_factory, _FakeRouter(deltas=["x"], raise_after=0))
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="我推门进去。",
            scenario=_scenario(),
        )
    )
    codes = [e[1].get("code") for e in events if e[0] == "error"]
    assert "generation_failed" in codes
    assert events[-1][1]["ok"] is False


# ── PR B: run resume / restart ───────────────────────────────────────


@pytest.mark.asyncio
async def test_start_run_retires_prior_active_run(monkeypatch):
    """开始/重新开始 ends any prior active run before creating the fresh one.

    Keeps the "at most one active run per scenario" invariant so the detail
    page's 继续游玩 always resumes the newest playthrough.
    """
    calls: list[str] = []
    run = _run()

    async def _end_active(session, user_id, scenario_id):
        calls.append("end_active")
        return 1

    async def _create_run(session, **kw):
        calls.append("create_run")
        return run

    async def _next_seq(session, run_id):
        return 1

    async def _add_message(session, **kw):
        return object()

    async def _bump(session, run_id, **kw):
        return None

    monkeypatch.setattr(repo, "end_active_runs_for_scenario", _end_active)
    monkeypatch.setattr(repo, "create_run", _create_run)
    monkeypatch.setattr(repo, "next_seq", _next_seq)
    monkeypatch.setattr(repo, "add_message", _add_message)
    monkeypatch.setattr(repo, "bump_run_activity", _bump)

    svc = StoryService(_fake_factory, _FakeRouter())
    result = await svc.start_run(
        user_id=run.user_id, scenario=_scenario(), player_identity={}
    )

    # Prior active run retired strictly before the new one is created.
    assert calls[:2] == ["end_active", "create_run"]
    assert result.run is run
    assert result.opening_bubbles  # opening GM bubbles generated + returned


# ── PR5: safety pre-check ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_turn_stream_safety_blocks_high_severity(patched_repo):
    """RED/PURPLE (ordinal ≥ 3) input is refused before any generation."""
    svc = StoryService(_fake_factory, _FakeRouter(), safety_agent=_FakeSafety(4))
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="（高危内容）",
            scenario=_scenario(),
        )
    )
    types = [e[0] for e in events]
    assert types == ["turn_start", "error", "turn_end"]
    assert events[1][1]["code"] == "safety_blocked"
    # Nothing generated or persisted.
    assert not any(e[0] == "text_delta" for e in events)
    assert not any(m["role"] == "player" for m in patched_repo["added"])


@pytest.mark.asyncio
async def test_turn_stream_safety_allows_low_severity(patched_repo):
    """Romance/adult (never a safety category → low ordinal) passes through."""
    svc = StoryService(_fake_factory, _FakeRouter(), safety_agent=_FakeSafety(1))
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="我靠近他。",
            scenario=_scenario(),
        )
    )
    types = [e[0] for e in events]
    assert types[-1] == "turn_end"
    assert events[-1][1]["ok"] is True
    assert any(e[0] == "text_delta" for e in events)


@pytest.mark.asyncio
async def test_turn_stream_safety_fails_open_on_error(patched_repo):
    """A classifier that raises must not block the turn (fail-open, logged)."""

    class _BoomSafety:
        async def classify(self, message, **kw):
            raise RuntimeError("classifier down")

    svc = StoryService(_fake_factory, _FakeRouter(), safety_agent=_BoomSafety())
    events = await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="继续。",
            scenario=_scenario(),
        )
    )
    assert events[-1][1]["ok"] is True


# ── PR5: credit debit parity ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_turn_stream_insufficient_credits(patched_repo, monkeypatch):
    """A paid model with a balance below cost is refused before generating."""
    import heart.billing as billing

    async def _low_balance(session, user_id):
        return 0

    monkeypatch.setattr(billing, "get_balance", _low_balance)

    run = patched_repo["run"]
    run.model = "claude"  # non-zero llm_cost_fen
    svc = StoryService(_fake_factory, _FakeRouter())
    events = await _collect(
        svc.process_turn_stream(
            run_id=run.id, user_id=run.user_id, player_text="hi", scenario=_scenario()
        )
    )
    types = [e[0] for e in events]
    assert types == ["turn_start", "error", "turn_end"]
    assert events[1][1]["code"] == "insufficient_credits"
    assert not any(e[0] == "text_delta" for e in events)


@pytest.mark.asyncio
async def test_turn_stream_charges_after_success(patched_repo, monkeypatch):
    """A paid, affordable turn deducts credits once after generation."""
    import heart.billing as billing

    charged: list[tuple] = []

    async def _ok_balance(session, user_id):
        return 10_000

    async def _deduct(session, user_id, amount, idem, type_str="consume_text"):
        charged.append((amount, idem, type_str))
        return 10_000 - amount

    monkeypatch.setattr(billing, "get_balance", _ok_balance)
    monkeypatch.setattr(billing, "deduct_credits", _deduct)

    run = patched_repo["run"]
    run.model = "claude"
    svc = StoryService(_fake_factory, _FakeRouter())
    events = await _collect(
        svc.process_turn_stream(
            run_id=run.id, user_id=run.user_id, player_text="hi", scenario=_scenario()
        )
    )
    assert events[-1][1]["ok"] is True
    assert len(charged) == 1
    assert charged[0][2] == "consume_llm"
    assert charged[0][1].startswith("story_turn:")
    assert charged[0][1].endswith(":llm")


@pytest.mark.asyncio
async def test_deepseek_turn_is_free(patched_repo, monkeypatch):
    """Default DeepSeek model (0 fen) never touches billing."""
    import heart.billing as billing

    called = {"balance": 0, "deduct": 0}

    async def _balance(session, user_id):
        called["balance"] += 1
        return 0

    async def _deduct(session, user_id, amount, idem, type_str="consume_text"):
        called["deduct"] += 1
        return 0

    monkeypatch.setattr(billing, "get_balance", _balance)
    monkeypatch.setattr(billing, "deduct_credits", _deduct)

    svc = StoryService(_fake_factory, _FakeRouter())  # run.model == deepseek
    await _collect(
        svc.process_turn_stream(
            run_id=patched_repo["run"].id,
            user_id=patched_repo["run"].user_id,
            player_text="hi",
            scenario=_scenario(),
        )
    )
    assert called == {"balance": 0, "deduct": 0}


# ── PR5: rolling summary ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_maybe_summarize_folds_when_tail_grows(monkeypatch):
    """Once pending messages exceed the trigger, older ones fold into summary."""
    from heart.ss09_story.models import StoryMessage

    run = _run()

    async def _get_run(session, run_id, user_id):
        return run

    # Return SUMMARIZE_TRIGGER + a few messages so a fold is due.
    n = service_mod.SUMMARIZE_TRIGGER + 4
    now = datetime.now(timezone.utc)
    msgs = [
        StoryMessage(
            id=uuid4(), run_id=run.id, turn_id=uuid4(), seq=i + 1,
            role="player" if i % 2 == 0 else "gm", kind="narration",
            npc_name=None, content=f"line {i}", created_at=now,
        )
        for i in range(n)
    ]

    async def _list_messages(session, run_id, after_seq=0, limit=200):
        return msgs

    bumped: list[dict] = []

    async def _bump(session, run_id, **kw):
        bumped.append(kw)

    monkeypatch.setattr(repo, "get_run", _get_run)
    monkeypatch.setattr(repo, "list_messages", _list_messages)
    monkeypatch.setattr(repo, "bump_run_activity", _bump)

    router = _FakeRouter()
    svc = StoryService(_fake_factory, router)
    await svc._maybe_summarize(run.id, run.user_id, _scenario())

    assert len(router.cheap_calls) == 1  # summariser invoked once
    assert len(bumped) == 1
    assert bumped[0]["summary"].startswith("前情提要")
    # Watermark advances to the last folded message (keeps recent window live).
    expected_wm = msgs[-service_mod.gm_prompt.RECENT_TURNS_WINDOW - 1].seq
    assert bumped[0]["summary_watermark"] == expected_wm


# ── PR C2: per-minute playtime billing ───────────────────────────────


class _BillingRow:
    """Stand-in for the get_run_billing result row."""

    def __init__(self, status="active", billed_minutes=0, last_billed_at=None):
        self.status = status
        self.billed_minutes = billed_minutes
        self.last_billed_at = last_billed_at


@pytest.mark.asyncio
async def test_charge_playtime_charges_one_minute(monkeypatch):
    """First heartbeat of a fresh active run bills minute 0 and advances it."""
    import heart.billing as billing

    charged: list[tuple] = []
    advanced: list[int] = []

    async def _get_billing(session, run_id, user_id):
        return _BillingRow(status="active", billed_minutes=0, last_billed_at=None)

    async def _deduct(session, user_id, amount, idem, type_str="consume_text"):
        charged.append((amount, idem, type_str))
        return 5_000 - amount

    async def _advance(session, run_id, minute, now):
        advanced.append(minute)

    monkeypatch.setattr(repo, "get_run_billing", _get_billing)
    monkeypatch.setattr(repo, "advance_billed_minute", _advance)
    monkeypatch.setattr(billing, "deduct_credits", _deduct)

    svc = StoryService(_fake_factory, _FakeRouter())
    run = _run()
    status, balance = await svc.charge_playtime(run.id, run.user_id)

    assert status == "charged"
    assert balance == 5_000 - 100  # 1 悠悠币 = 100 fen
    assert len(charged) == 1
    assert charged[0][0] == 100
    assert charged[0][1] == f"story_time:{run.id}:0"
    assert charged[0][2] == "story_time"
    assert advanced == [0]


@pytest.mark.asyncio
async def test_charge_playtime_throttled(monkeypatch):
    """A heartbeat arriving too soon after the last charge bills nothing."""
    import heart.billing as billing

    charged: list[tuple] = []

    async def _get_billing(session, run_id, user_id):
        recent = datetime.now(timezone.utc)
        return _BillingRow(status="active", billed_minutes=3, last_billed_at=recent)

    async def _deduct(session, user_id, amount, idem, type_str="consume_text"):
        charged.append((amount, idem, type_str))
        return 0

    monkeypatch.setattr(repo, "get_run_billing", _get_billing)
    monkeypatch.setattr(billing, "deduct_credits", _deduct)

    svc = StoryService(_fake_factory, _FakeRouter())
    status, _ = await svc.charge_playtime(uuid4(), uuid4())

    assert status == "throttled"
    assert charged == []  # never billed


@pytest.mark.asyncio
async def test_charge_playtime_insufficient(monkeypatch):
    """Balance below a minute's cost → insufficient, no advance, save preserved."""
    import heart.billing as billing

    advanced: list[int] = []

    async def _get_billing(session, run_id, user_id):
        return _BillingRow(status="active", billed_minutes=7, last_billed_at=None)

    async def _deduct(session, user_id, amount, idem, type_str="consume_text"):
        raise billing.InsufficientCreditsError(amount, 40)

    async def _advance(session, run_id, minute, now):
        advanced.append(minute)

    monkeypatch.setattr(repo, "get_run_billing", _get_billing)
    monkeypatch.setattr(repo, "advance_billed_minute", _advance)
    monkeypatch.setattr(billing, "deduct_credits", _deduct)

    svc = StoryService(_fake_factory, _FakeRouter())
    status, balance = await svc.charge_playtime(uuid4(), uuid4())

    assert status == "insufficient"
    assert balance == 40
    assert advanced == []  # minute counter not advanced when unpaid


@pytest.mark.asyncio
async def test_charge_playtime_inactive_run(monkeypatch):
    """A missing / non-active run bills nothing."""
    async def _get_billing(session, run_id, user_id):
        return None

    monkeypatch.setattr(repo, "get_run_billing", _get_billing)

    svc = StoryService(_fake_factory, _FakeRouter())
    status, _ = await svc.charge_playtime(uuid4(), uuid4())
    assert status == "inactive"


@pytest.mark.asyncio
async def test_maybe_summarize_noop_below_trigger(monkeypatch):
    """Below the trigger threshold nothing is summarised."""
    from heart.ss09_story.models import StoryMessage

    run = _run()

    async def _get_run(session, run_id, user_id):
        return run

    now = datetime.now(timezone.utc)
    few = [
        StoryMessage(
            id=uuid4(), run_id=run.id, turn_id=uuid4(), seq=i + 1, role="gm",
            kind="narration", npc_name=None, content="x", created_at=now,
        )
        for i in range(3)
    ]

    async def _list_messages(session, run_id, after_seq=0, limit=200):
        return few

    bumped: list[dict] = []

    async def _bump(session, run_id, **kw):
        bumped.append(kw)

    monkeypatch.setattr(repo, "get_run", _get_run)
    monkeypatch.setattr(repo, "list_messages", _list_messages)
    monkeypatch.setattr(repo, "bump_run_activity", _bump)

    router = _FakeRouter()
    svc = StoryService(_fake_factory, router)
    await svc._maybe_summarize(run.id, run.user_id, _scenario())

    assert router.cheap_calls == []
    assert bumped == []
