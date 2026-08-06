"""Unit: proactive message content is split into bubble segments.

The SS06 proactive message is a single content string in the DB. Regular chat
replies are split into dialog vs action bubbles by ss05_composer.split_response;
proactive messages must get the same treatment so an opening like
"（叹了口气）在忙吗？" renders as a grey action pill + a text bubble instead of
one run-together bubble.

Tests target the module-level ``_serialize_message`` helper directly so no app
init / DEEPSEEK_API_KEY / DB is required (create_app pulls in the LLM router).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from heart.api.routes_proactive import _serialize_message


def _msg(content: str):
    return SimpleNamespace(
        id=uuid4(),
        character_id="rin",
        content=content,
        trigger_type="scheduled",
        created_at=datetime.now(timezone.utc),
    )


def test_action_and_dialog_split_into_segments():
    msg = _msg("（轻轻叹了口气）在忙吗？突然有点想你了。")
    out = _serialize_message(msg)

    segments = out["segments"]
    # Action bracket becomes its own grey pill; dialog is a separate text bubble.
    assert segments[0] == {"kind": "action", "content": "轻轻叹了口气"}
    assert any(s["kind"] == "text" and "在忙吗" in s["content"] for s in segments)
    # Original content is preserved for back-compat / previews.
    assert out["content"] == msg.content
    assert out["id"] == str(msg.id)


def test_plain_message_is_single_text_segment():
    msg = _msg("在忙吗？想你了。")
    segments = _serialize_message(msg)["segments"]

    assert all(s["kind"] == "text" for s in segments)
    joined = "".join(s["content"] for s in segments).replace(" ", "")
    assert joined == "在忙吗？想你了。"
