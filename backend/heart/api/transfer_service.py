"""转账 (WeChat-style transfer) service — parse/serialize + LLM accept decision.

The transfer is a *roleplay affection gesture*, not real billing: the amount is
narrative (5.20 / 13.14 / a big number to insist), and the character decides
whether to 收下 (accept) based on personality and how hard the user is pushing.

Storage: chat_messages.kind='transfer' (role=user) carries a JSON `content`:
    {"transfer_id","amount","note","status","direction"}
status ∈ {pending, accepted, declined}. The character's receipt bubble is a
separate kind='transfer_receipt' row (role=assistant).

This module is pure/testable — no DB, no network beyond the injected router.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

TRANSFER_KIND = "transfer"
RECEIPT_KIND = "transfer_receipt"

# Amount guard rails — narrative money, but keep it sane so the bubble renders.
MAX_AMOUNT = 999_999_999.0
MIN_AMOUNT = 0.001


@dataclass
class TransferData:
    transfer_id: str
    amount: float
    note: str
    status: str  # pending | accepted | declined
    direction: str = "out"  # always 'out' for now (user → character)

    def to_json(self) -> str:
        return json.dumps(
            {
                "transfer_id": self.transfer_id,
                "amount": round(self.amount, 3),
                "note": self.note,
                "status": self.status,
                "direction": self.direction,
            },
            ensure_ascii=False,
        )


def normalize_amount(raw: Any) -> float:
    """Clamp/round an incoming amount; raise ValueError if not a usable number."""
    try:
        amt = round(float(raw), 3)
    except (TypeError, ValueError) as e:
        raise ValueError("金额格式不正确") from e
    if amt < MIN_AMOUNT:
        raise ValueError("金额太小")
    if amt > MAX_AMOUNT:
        raise ValueError("金额太大")
    return amt


def parse_transfer(content: Optional[str]) -> Optional[TransferData]:
    """Parse a transfer row's JSON `content`. Returns None if it isn't one."""
    if not content:
        return None
    try:
        d = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict) or "transfer_id" not in d or "amount" not in d:
        return None
    try:
        amount = float(d["amount"])
    except (TypeError, ValueError):
        return None
    return TransferData(
        transfer_id=str(d["transfer_id"]),
        amount=amount,
        note=str(d.get("note") or ""),
        status=str(d.get("status") or "pending"),
        direction=str(d.get("direction") or "out"),
    )


def transfer_history_line(role: str, content: Optional[str]) -> Optional[str]:
    """Render a transfer/receipt row as a natural-language memory line for the LLM.

    Returns None if the row isn't a transfer marker (caller keeps it as-is).
    The receipt row (assistant) carries no independent state — the user's
    transfer row already encodes accepted/declined, so the receipt maps to the
    same "你收下了" line and we return an empty sentinel to drop it.
    """
    data = parse_transfer(content)
    if data is None:
        return None
    amt = f"{data.amount:.2f}".rstrip("0").rstrip(".")
    note_part = f"，附言：{data.note}" if data.note else ""
    if data.status == "accepted":
        return f"（对方给你转账 {amt} 元{note_part}，你收下了）"
    if data.status == "declined":
        return f"（对方给你转账 {amt} 元{note_part}，你没有收）"
    return f"（对方给你转账 {amt} 元{note_part}，还没处理）"


@dataclass
class TransferDecision:
    accept: bool
    reply: str


_DECISION_SYS = """你正在扮演角色「{name}」。{persona}{backstory}

对方给你转了 {amount} 元{note_part}。

根据你的性格、你俩的关系、对方态度，决定收不收，并回应一句话(≤30字，可含动作)。
- 矜持/高冷角色通常不收或推辞；关系好、对方坚持时更可能收。
- 金额异常大/小或对方开玩笑时可不收。
- 保持人设，自然反应。

输出 JSON: {{"accept": true或false, "reply": "一句话"}}"""


def build_decision_prompt(
    *,
    name: str,
    persona: str,
    backstory: Optional[str],
    amount: float,
    note: str,
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build the messages array for the accept/decline decision call."""
    amt = f"{amount:.2f}".rstrip("0").rstrip(".")
    note_part = f"，附言写着「{note}」" if note else ""
    persona_part = f"\n你的人设：{persona}" if persona else ""
    backstory_part = f"\n背景：{backstory}" if backstory else ""
    sys = _DECISION_SYS.format(
        name=name,
        persona=persona_part,
        backstory=backstory_part,
        amount=amt,
        note_part=note_part,
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": sys}]
    # Recent dialog gives the model the user's tone / insistence to weigh.
    for turn in history[-12:]:
        r = turn.get("role")
        if r in ("user", "assistant"):
            messages.append({"role": r, "content": turn.get("content", "")})
    messages.append(
        {
            "role": "user",
            "content": f"转账 {amt} 元{note_part}",
        }
    )
    return messages


def parse_decision(raw: str, *, name: str) -> TransferDecision:
    """Parse the LLM JSON decision. Falls back to a safe decline on garbage."""
    text = (raw or "").strip()
    # Strip ```json fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    # Grab the first {...} block so trailing prose doesn't break json.loads.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    elif start != -1 and end == -1:
        # Truncated JSON (max_tokens hit mid-reply) — try closing it.
        text = text[start:] + '"}'
    try:
        d = json.loads(text)
        accept = bool(d.get("accept"))
        reply = str(d.get("reply") or "").strip()
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning("transfer_decision_parse_failed", raw=raw[:200])
        return TransferDecision(accept=False, reply="……你这是干嘛，我不能收你的钱。")
    if not reply:
        reply = "嗯……我收下了。" if accept else "我不能收你这个。"
    return TransferDecision(accept=accept, reply=reply)


async def decide_transfer(
    *,
    model_router: Any,
    name: str,
    persona: str,
    backstory: Optional[str],
    amount: float,
    note: str,
    history: list[dict[str, str]],
) -> TransferDecision:
    """Run the one-shot LLM decision. Safe-declines if the router is unavailable."""
    if model_router is None:
        return TransferDecision(accept=False, reply="（愣了一下）现在……先别转钱给我。")
    messages = build_decision_prompt(
        name=name,
        persona=persona,
        backstory=backstory,
        amount=amount,
        note=note,
        history=history,
    )
    try:
        raw = await model_router.call_cheap(
            messages=messages,
            temperature=0.8,
            max_tokens=600,
            json_mode=True,
            agent_name=f"Transfer.{name}",
        )
    except Exception:
        logger.exception("transfer_decision_llm_failed", name=name)
        return TransferDecision(accept=False, reply="（一时没反应过来）等等，先别转。")
    return parse_decision(raw, name=name)
