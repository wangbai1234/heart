"""Unit tests for transfer_service (parse/serialize/decision-parse/history-line)."""

from __future__ import annotations

import json

import pytest

from heart.api.transfer_service import (
    TransferData,
    build_decision_prompt,
    normalize_amount,
    parse_decision,
    parse_transfer,
    transfer_history_line,
)


def test_normalize_amount_valid():
    assert normalize_amount(5.2) == 5.2
    assert normalize_amount("13.14") == 13.14
    assert normalize_amount(1) == 1.0


@pytest.mark.parametrize("bad", [0, -1, 0.0001, 1_000_000_000, "abc", None])
def test_normalize_amount_rejects(bad):
    with pytest.raises(ValueError):
        normalize_amount(bad)


def test_normalize_amount_range_bounds():
    assert normalize_amount(0.001) == 0.001
    assert normalize_amount(999_999_999) == 999_999_999.0


def test_transfer_roundtrip():
    t = TransferData(transfer_id="t1", amount=5.2, note="奶茶", status="pending")
    parsed = parse_transfer(t.to_json())
    assert parsed is not None
    assert parsed.transfer_id == "t1"
    assert parsed.amount == 5.2
    assert parsed.note == "奶茶"
    assert parsed.status == "pending"
    assert parsed.direction == "out"


@pytest.mark.parametrize("content", [None, "", "not json", "{}", '{"amount": 1}'])
def test_parse_transfer_rejects_non_transfer(content):
    assert parse_transfer(content) is None


def test_history_line_states():
    acc = TransferData(transfer_id="t", amount=5.2, note="奶茶", status="accepted").to_json()
    dec = TransferData(transfer_id="t", amount=13.14, note="", status="declined").to_json()
    pen = TransferData(transfer_id="t", amount=100, note="", status="pending").to_json()
    assert "收下了" in transfer_history_line("user", acc)
    assert "奶茶" in transfer_history_line("user", acc)
    assert "没有收" in transfer_history_line("user", dec)
    assert "还没处理" in transfer_history_line("user", pen)


def test_history_line_none_for_non_transfer():
    assert transfer_history_line("user", "普通聊天内容") is None


def test_parse_decision_accept():
    d = parse_decision('{"accept": true, "reply": "谢谢你，我收下了。"}', name="小北")
    assert d.accept is True
    assert "收下" in d.reply


def test_parse_decision_decline():
    d = parse_decision('{"accept": false, "reply": "我不能要你的钱。"}', name="小北")
    assert d.accept is False


def test_parse_decision_with_code_fence():
    raw = '```json\n{"accept": true, "reply": "嗯。"}\n```'
    d = parse_decision(raw, name="小北")
    assert d.accept is True
    assert d.reply == "嗯。"


def test_parse_decision_with_trailing_prose():
    raw = '好的，我的决定是：{"accept": false, "reply": "别闹。"} 就这样。'
    d = parse_decision(raw, name="小北")
    assert d.accept is False
    assert d.reply == "别闹。"


def test_parse_decision_garbage_safe_declines():
    d = parse_decision("完全不是 JSON 的一段话", name="小北")
    assert d.accept is False
    assert d.reply  # non-empty fallback


def test_parse_decision_truncated_json_repair():
    # LLM hit max_tokens mid-reply → no closing `"}`. Parser tries appending `"}`.
    raw = '{"accept": true, "reply": "（轻叹'
    d = parse_decision(raw, name="霍时予")
    assert d.accept is True
    assert d.reply == "（轻叹"  # salvaged prefix


def test_parse_decision_empty_reply_gets_fallback():
    assert parse_decision('{"accept": true, "reply": ""}', name="小北").reply
    assert parse_decision('{"accept": false, "reply": ""}', name="小北").reply


def test_build_decision_prompt_shape():
    msgs = build_decision_prompt(
        name="周予燃",
        persona="高冷矜持",
        backstory="霸道总裁",
        amount=5.2,
        note="给你买奶茶",
        history=[{"role": "user", "content": "在吗"}, {"role": "assistant", "content": "在"}],
    )
    assert msgs[0]["role"] == "system"
    assert "周予燃" in msgs[0]["content"]
    assert "5.2" in msgs[0]["content"]
    assert "给你买奶茶" in msgs[0]["content"]
    # history + trailing user prompt present
    assert msgs[-1]["role"] == "user"
    assert any(m["content"] == "在吗" for m in msgs)


def test_build_decision_prompt_caps_history():
    long_hist = [{"role": "user", "content": str(i)} for i in range(40)]
    msgs = build_decision_prompt(
        name="x", persona="", backstory=None, amount=1, note="", history=long_hist
    )
    # system + <=12 history + trailing user
    assert len(msgs) <= 1 + 12 + 1


def test_to_json_rounds_amount():
    t = TransferData(transfer_id="t", amount=5.1999, note="", status="pending")
    assert json.loads(t.to_json())["amount"] == 5.2
