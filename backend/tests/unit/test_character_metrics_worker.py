from datetime import date

import pytest

from heart.workers.character_metrics_worker import support_low_heat_characters


class _Row:
    def __init__(self, character_id: str, amount: int):
        self.id = character_id
        self.amount = amount


class _Result:
    rowcount = 2

    def __iter__(self):
        return iter([_Row("ugc_low_1", 50), _Row("ugc_low_2", 100)])


class _Session:
    def __init__(self):
        self.statement = None
        self.params = None

    async def execute(self, statement, params):
        self.statement = str(statement)
        self.params = params
        return _Result()


@pytest.mark.asyncio
async def test_low_heat_support_is_public_approved_ugc_and_day_scoped():
    session = _Session()
    day = date(2026, 8, 31)

    supported = await support_low_heat_characters(session, support_day=day, limit=5)

    assert supported == [("ugc_low_1", 50), ("ugc_low_2", 100)]
    assert session.params == {"support_day": day, "limit": 5}
    assert "owner_user_id IS NOT NULL" in session.statement
    assert "visibility = 'public'" in session.statement
    assert "review_status = 'approved'" in session.statement
    assert "last_heat_support_date < :support_day" in session.statement
    assert "display_heat = c.display_heat + i.amount" in session.statement
    assert "real_view_count" not in session.statement
