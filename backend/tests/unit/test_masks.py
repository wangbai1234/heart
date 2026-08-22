"""Unit contracts for explicit user masks."""

import pytest
from pydantic import ValidationError

from heart.api.routes_masks import MaskInput


def test_mask_input_strips_required_text() -> None:
    value = MaskInput(name="  小满  ", bio="  喜欢摄影  ")
    assert value.name == "小满"
    assert value.bio == "喜欢摄影"
    assert value.gender == "unspecified"


@pytest.mark.parametrize("field", ["name", "bio"])
def test_mask_input_rejects_whitespace_only(field: str) -> None:
    payload = {"name": "小满", "bio": "喜欢摄影", field: "   "}
    with pytest.raises(ValidationError):
        MaskInput(**payload)
