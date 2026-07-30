"""Unit tests for UGC opening/intro draft fields (creator authoring path).

Covers the write side of the opening-scene redesign:
  1. CharacterDraft accepts + round-trips `opening` / `intro` (extra="forbid"
     would otherwise reject them).
  2. build_soul_spec_from_draft treats them as presentation/playback fields —
     it must NOT fail on them and must NOT leak them into the SoulSpec persona.
  3. The /characters/opening-preview endpoint validates persona length and
     degrades gracefully when the model router is unavailable.
"""

from __future__ import annotations

import pytest

from fastapi import HTTPException

from heart.core.auth import TokenData
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft

_OPENING = "（她把伞往你这边倾了倾。）\n这么巧？\n还是说，你一直在等我？"
_INTRO = "雨夜救护车里遇见的急诊科医生，话不多，手很稳。"


def _draft(**overrides) -> CharacterDraft:
    base = dict(
        display_name={"zh": "林医生"},
        persona="急诊科主治医师，外冷内热，习惯用行动而非语言表达关心。" * 2,
        greeting_style="cool",
    )
    base.update(overrides)
    return CharacterDraft(**base)


def test_draft_accepts_opening_and_intro():
    d = _draft(opening=_OPENING, intro=_INTRO)
    assert d.opening == _OPENING
    assert d.intro == _INTRO


def test_draft_round_trips_through_json():
    d = _draft(opening=_OPENING, intro=_INTRO)
    restored = CharacterDraft.model_validate(d.model_dump())
    assert restored.opening == _OPENING
    assert restored.intro == _INTRO


def test_draft_opening_and_intro_optional():
    d = _draft()
    assert d.opening is None
    assert d.intro is None


def test_draft_opening_max_length():
    with pytest.raises(ValueError):
        _draft(opening="超" * 2001)


def test_draft_intro_max_length():
    with pytest.raises(ValueError):
        _draft(intro="超" * 501)


def test_spec_builder_ignores_opening_and_intro():
    """opening/intro are presentation fields — the spec builder must not consume
    them into the persona, and must not raise on their presence."""
    with_fields = build_soul_spec_from_draft(
        _draft(opening=_OPENING, intro=_INTRO), character_id="cid_a"
    )
    without = build_soul_spec_from_draft(_draft(), character_id="cid_b")
    # The authored opening text must never leak into the model-facing persona.
    assert _OPENING not in with_fields.model_dump_json()
    assert _INTRO not in with_fields.model_dump_json()
    # Presence of the fields must not perturb the generated spec structure.
    assert type(with_fields) is type(without)


# ── /characters/opening-preview endpoint ───────────────────────────────

_USER = TokenData(user_id="550e8400-e29b-41d4-a716-446655440000", email="t@example.com")


class _StubRouter:
    def __init__(self, out: str = "（她抬眼看你。）\n来了。") -> None:
        self.out = out
        self.calls: list[dict] = []

    async def call_main(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        return self.out


async def test_preview_rejects_short_persona():
    from heart.api.routes_characters import OpeningPreviewRequest, preview_opening

    with pytest.raises(HTTPException) as exc:
        await preview_opening(
            OpeningPreviewRequest(persona="太短"), current_user=_USER
        )
    assert exc.value.status_code == 422


async def test_preview_503_when_router_unavailable(monkeypatch):
    import heart.api.wiring as wiring
    from heart.api.routes_characters import OpeningPreviewRequest, preview_opening

    monkeypatch.setattr(wiring, "get_model_router", lambda: None)
    with pytest.raises(HTTPException) as exc:
        await preview_opening(
            OpeningPreviewRequest(persona="急诊科主治医师，外冷内热，习惯用行动表达关心。"),
            current_user=_USER,
        )
    assert exc.value.status_code == 503


async def test_preview_returns_opening_and_uses_main_model(monkeypatch):
    import heart.api.wiring as wiring
    from heart.api.routes_characters import OpeningPreviewRequest, preview_opening

    stub = _StubRouter()
    monkeypatch.setattr(wiring, "get_model_router", lambda: stub)
    result = await preview_opening(
        OpeningPreviewRequest(
            display_name="林医生",
            persona="急诊科主治医师，外冷内热，习惯用行动而非语言表达关心。",
            tags=["医生", "外冷内热"],
            greeting_style="cool",
        ),
        current_user=_USER,
    )
    assert result["opening"] == stub.out
    # Authoring path must use the high-quality main model, not call_cheap.
    assert len(stub.calls) == 1


async def test_preview_502_on_empty_generation(monkeypatch):
    import heart.api.wiring as wiring
    from heart.api.routes_characters import OpeningPreviewRequest, preview_opening

    monkeypatch.setattr(wiring, "get_model_router", lambda: _StubRouter(out="   "))
    with pytest.raises(HTTPException) as exc:
        await preview_opening(
            OpeningPreviewRequest(persona="急诊科主治医师，外冷内热，习惯用行动表达关心。"),
            current_user=_USER,
        )
    assert exc.value.status_code == 502
