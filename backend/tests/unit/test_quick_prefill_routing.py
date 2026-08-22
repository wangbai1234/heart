from __future__ import annotations

import asyncio
import json

import pytest

from heart.core.auth import TokenData
from heart.infra.model_catalog import (
    MODEL_BY_ID,
    model_ids_by_ascending_coin_cost,
    model_ids_by_descending_coin_cost,
)

_USER = TokenData(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    email="creator@example.com",
)


class _RouterStub:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    async def call_for(self, model: str, **kwargs):  # noqa: ANN003
        self.kwargs = {"model": model, **kwargs}
        payload = {
            "age_range": "25-30",
            "greeting_style": "cool",
            "sliders": {
                "warmth": 0.4,
                "talkativeness": 0.5,
                "directness": 0.7,
                "humor": 0.3,
                "playfulness": 0.2,
                "steadiness": 0.8,
            },
            "tagline": "他总在最忙的夜里保持清醒",
            "intro": "沈砚是市中心医院的急诊科医生，值夜班时话很少，却会记住每位同事的习惯。他判断果断，不擅长解释关心，常用递来的一杯热水或替人收尾表达在意。",
            "one_liner": "那场被他独自承担责任的抢救事故，正因你的出现再次浮出水面。",
            "archetype_label": "急诊科医生",
            "backstory": "沈砚成长在一个习惯用成绩衡量一切的家庭，很早就学会把情绪收起来。一次急诊抢救中，他为了保护年轻同事承担了全部责任，从此更相信行动而非辩解。如今他依然留在最忙的夜班，既想证明自己能够守住所有人，也害怕再次因为一个决定失去重要的人。",
            "tags": ["急诊医生", "克制", "护短"],
            "catchphrases": ["过来。", "别逞强。", "我在。"],
            "speech_samples": [
                "先坐下，剩下的我来处理。",
                "你可以生气，但别拿自己的身体赌。",
                "我没在等你，只是还没下班。",
            ],
            "soul_profile": {
                "wound_essence": "曾因一次关键决定让信任自己的人受伤",
                "wound_manifest": "越在意越倾向独自承担，不给别人共同选择的机会",
                "wound_defense": "用专业判断和冷静语气隔开自己的愧疚",
                "private_truth": "他并不相信自己真的值得被无条件留下",
                "desire_surface": "把每一件事处理妥当",
                "desire_hidden": "有人能看见他的疲惫却不逼他解释",
                "desire_deepest": "允许自己被照顾而不因此失去价值",
                "fear_ultimate": "自己的选择再次伤害最重要的人",
                "fear_daily": "在需要休息时暴露出无法掌控局面的脆弱",
                "fear_shadow": "所谓负责只是他拒绝信任别人的借口",
                "belief_self": "只有保持可靠才有资格留在别人身边",
                "belief_others": "多数承诺会在真正的压力面前动摇",
                "belief_love": "亲密是共同承担，而不是单方面拯救",
                "belief_time": "时间不会消除错误，只会检验人如何带着错误生活",
                "softening_triggers": ["对方尊重他的沉默", "有人主动分担琐碎责任"],
            },
            "opening": "（急诊室外的雨声压过了走廊尽头的脚步，沈砚刚摘下手套，袖口还沾着未干的水迹。）\n你不该在这个时间来。\n（他看了你一眼，把原本要丢进垃圾桶的纸杯放回桌面，又重新倒了一杯温水。）\n先坐。有什么话，等你的手不再发抖了再说。",
            "theme_preset_id": "ocean_depth",
        }
        return json.dumps(payload, ensure_ascii=False), model


class _RetryRouterStub(_RouterStub):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def call_for(self, model: str, **kwargs):  # noqa: ANN003
        response, served_model = await super().call_for(model, **kwargs)
        self.calls += 1
        if self.calls == 1:
            duplicate = json.loads(response)
            duplicate["intro"] = duplicate["tagline"]
            response = json.dumps(duplicate, ensure_ascii=False)
        return response, served_model


def test_authoring_model_chain_is_complete_and_descends_by_coin_cost():
    chain = model_ids_by_descending_coin_cost()

    assert set(chain) == set(MODEL_BY_ID)
    costs = [MODEL_BY_ID[model_id].cost_coins for model_id in chain]
    assert costs == sorted(costs, reverse=True)


def test_availability_model_chain_starts_with_gemini_and_ascends_by_coin_cost():
    chain = model_ids_by_ascending_coin_cost()

    assert chain[0] == "gemini-3.1"
    assert set(chain) == set(MODEL_BY_ID)
    costs = [MODEL_BY_ID[model_id].cost_coins for model_id in chain]
    assert costs == sorted(costs)


@pytest.mark.asyncio
async def test_quick_prefill_uses_gemini_first_availability_chain(monkeypatch):
    import heart.api.wiring as wiring
    from heart.api.routes_characters import QuickPrefillRequest, quick_prefill

    stub = _RouterStub()
    monkeypatch.setattr(wiring, "get_model_router", lambda: stub)

    result = await quick_prefill(
        QuickPrefillRequest(
            display_name="沈砚",
            gender="male",
            persona="外表冷淡克制，实际非常护短，习惯用行动表达关心的急诊科医生。",
        ),
        current_user=_USER,
    )

    chain = model_ids_by_ascending_coin_cost()
    assert result.greeting_style == "cool"
    assert stub.kwargs is not None
    assert stub.kwargs["model"] == chain[0]
    assert stub.kwargs["failover"] == list(chain[1:])
    assert stub.kwargs["json_mode"] is True
    assert stub.kwargs["attempt_timeout_s"] == 10.0
    assert stub.kwargs["max_tokens"] == 2200


@pytest.mark.asyncio
async def test_quick_prefill_retries_when_public_sections_repeat(monkeypatch):
    import heart.api.wiring as wiring
    from heart.api.routes_characters import QuickPrefillRequest, quick_prefill

    stub = _RetryRouterStub()
    monkeypatch.setattr(wiring, "get_model_router", lambda: stub)

    result = await quick_prefill(
        QuickPrefillRequest(
            display_name="沈砚",
            gender="male",
            persona="外表冷淡克制，实际非常护短，习惯用行动表达关心的急诊科医生。",
        ),
        current_user=_USER,
    )

    assert stub.calls == 2
    assert result.intro != result.tagline
    assert stub.kwargs is not None
    assert stub.kwargs["failover"] == []


@pytest.mark.asyncio
async def test_quick_prefill_has_a_whole_request_timeout(monkeypatch):
    import heart.api.routes_characters as routes
    import heart.api.wiring as wiring

    class _SlowRouter:
        async def call_for(self, model: str, **kwargs):  # noqa: ANN003
            await asyncio.sleep(1)
            return "{}", model

    monkeypatch.setattr(wiring, "get_model_router", lambda: _SlowRouter())
    monkeypatch.setattr(routes, "_QUICK_PREFILL_TOTAL_TIMEOUT_S", 0.01)

    with pytest.raises(routes.HTTPException) as exc:
        await routes.quick_prefill(
            routes.QuickPrefillRequest(
                display_name="沈砚",
                gender="male",
                persona="外表冷淡克制，实际非常护短，习惯用行动表达关心的急诊科医生。",
            ),
            current_user=_USER,
        )

    assert exc.value.status_code == 504
