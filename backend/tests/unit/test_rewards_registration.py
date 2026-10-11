"""Rewards availability must not depend on domestic payment providers."""

import pytest
from fastapi import FastAPI

from heart.api.main import _register_mode_specific_routers


@pytest.mark.parametrize("international", [False, True])
def test_campaigns_remain_available_without_reenabling_afdian(international):
    app = FastAPI()
    _register_mode_specific_routers(app, international)
    paths = app.openapi()["paths"]
    for path in (
        "/api/invite/status",
        "/api/lottery/status",
        "/api/lottery/draw",
        "/api/rewards/coupons",
        "/api/rewards/coupons/{coupon_id}/activate",
        "/api/commission/balance",
        "/api/commission/spend",
        "/api/promotions/status",
        "/api/promotions/submit",
        "/api/admin/promotions/pending",
    ):
        assert path in paths
    assert ("/api/webhooks/afdian" in paths) is not international
