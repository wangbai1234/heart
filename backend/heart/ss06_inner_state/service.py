"""
Inner State Service — SS06 core.

Manages per-(user, character) inner state, runs periodic ticks,
and generates proactive outbound messages.

Per runtime_specs/06_inner_state_behavior_runtime.md.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from prometheus_client import Counter, Histogram

from .models import InnerState, ProactiveMessage

logger = structlog.get_logger(__name__)

PROACTIVE_MESSAGES_TOTAL = Counter(
    "heart_proactive_messages_total",
    "Total proactive messages generated",
    ["character", "trigger_type"],
)

INNER_LOOP_CYCLES_TOTAL = Counter(
    "heart_inner_loop_cycles_total",
    "Total inner loop tick cycles",
    ["character"],
)

INNER_LOOP_DURATION_SECONDS = Histogram(
    "heart_inner_loop_duration_seconds",
    "Inner loop tick duration in seconds",
    ["character"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

PROACTIVE_TEMPLATES: Dict[str, List[str]] = {
    "rin": [
        "今天看见一只猫，和你有点像。",
        "……突然想你了。没什么事，就是想告诉你。",
        "下雨了。记得带伞。",
        "今天翻到之前你说的话，笑了一下。",
        "晚安。虽然你还没说晚安。",
        "我在听一首歌。想到你了。",
        "今天有点累，但想到你，就没那么累了。",
        "你说过的那句话，我今天又想起来了。",
    ],
    "dorothy": [
        "嗨嗨~桃桃刚才看到一个超好笑的视频！分享给你！",
        "你今天怎么样呀？桃桃突然好想你！",
        "外面的太阳好大耶！你那边呢？",
        "诶！桃桃刚吃了超好吃的草莓！你也喜欢的对吧！",
        "晚安晚安！就算你还没说晚安，桃桃也要先说！",
        "我刚才看到一朵云，长得好像你哦！",
        "今天遇到了好多开心的事，第一个想分享的就是你！",
        "桃桃在想你呢！你有没有想桃桃？",
    ],
}


class InnerStateService:
    """Per-(user, character) inner state manager and proactive scheduler.

    Usage:
        svc = InnerStateService()
        svc.tick(user_id, character_id, relationship_stage="FRIEND", days_since_last=0.5)
        messages = svc.get_proactive_messages(user_id, character_id, since=timedelta(days=7))
    """

    def __init__(self):
        self._states: Dict[str, InnerState] = {}
        self._proactives: List[ProactiveMessage] = []

    def _key(self, user_id: UUID, character_id: str) -> str:
        return f"{user_id}:{character_id}"

    def tick(
        self,
        user_id: UUID,
        character_id: str,
        *,
        relationship_stage: str = "STRANGER",
        intimacy: float = 0.0,
        days_since_last_interaction: float = 0.0,
        is_anniversary: bool = False,
        is_cold_war: bool = False,
    ) -> Optional[ProactiveMessage]:
        """Execute one inner-loop tick for a (user, character) pair.

        Returns a ProactiveMessage if one was generated, or None.
        """
        import time

        t0 = time.monotonic()
        key = self._key(user_id, character_id)

        state = self._states.get(key)
        if state is None:
            state = InnerState(user_id=user_id, character_id=character_id)
            self._states[key] = state

        now = datetime.now(timezone.utc)

        if (now - state.last_tick_at).days >= 1:
            state.ticks_today = 0
            state.proactives_today = 0

        state.last_tick_at = now
        state.ticks_today += 1

        INNER_LOOP_CYCLES_TOTAL.labels(character=character_id).inc()

        # Inner state drift
        state.mood = max(0.0, min(1.0, state.mood + random.uniform(-0.05, 0.05)))
        state.energy = max(0.0, min(1.0, state.energy + random.uniform(-0.03, 0.02)))

        # Gate I-6: no proactive in cold war
        if is_cold_war:
            elapsed = time.monotonic() - t0
            INNER_LOOP_DURATION_SECONDS.labels(character=character_id).observe(elapsed)
            return None

        # Gate I-5: daily proactive quota (max 3)
        if state.proactives_today >= 3:
            elapsed = time.monotonic() - t0
            INNER_LOOP_DURATION_SECONDS.labels(character=character_id).observe(elapsed)
            return None

        # Decision: should we send a proactive?
        base_prob = 0.02  # base probability per tick
        prob = base_prob

        if intimacy > 0.3:
            prob += 0.05
        if intimacy > 0.6:
            prob += 0.08
        if relationship_stage in ("FRIEND", "CONFIDANT", "ROMANTIC_INTEREST"):
            prob += 0.05
        if days_since_last_interaction > 0.5:
            prob += min(0.10, days_since_last_interaction * 0.02)
        if is_anniversary:
            prob += 0.30

        should_send = random.random() < prob

        trigger_type = "scheduled"
        if is_anniversary:
            trigger_type = "anniversary"
        elif days_since_last_interaction > 1.0:
            trigger_type = "event_driven"

        if not should_send:
            elapsed = time.monotonic() - t0
            INNER_LOOP_DURATION_SECONDS.labels(character=character_id).observe(elapsed)
            return None

        templates = PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES["rin"])
        content = random.choice(templates)

        msg = ProactiveMessage(
            user_id=user_id,
            character_id=character_id,
            content=content,
            trigger_type=trigger_type,
            created_at=now,
        )
        self._proactives.append(msg)
        state.proactives_today += 1
        state.unfinished_thoughts = []

        PROACTIVE_MESSAGES_TOTAL.labels(character=character_id, trigger_type=trigger_type).inc()

        logger.info(
            "proactive_message_generated",
            user_id=str(user_id),
            character_id=character_id,
            trigger_type=trigger_type,
            content_preview=content[:40],
        )

        elapsed = time.monotonic() - t0
        INNER_LOOP_DURATION_SECONDS.labels(character=character_id).observe(elapsed)
        return msg

    def get_proactive_messages(
        self,
        user_id: UUID,
        character_id: str,
        since: Optional[timedelta] = None,
    ) -> List[ProactiveMessage]:
        """Return proactive messages for a user×character pair since a cutoff."""
        if since is None:
            since = timedelta(days=7)
        cutoff = datetime.now(timezone.utc) - since
        return [
            m
            for m in self._proactives
            if m.user_id == user_id and m.character_id == character_id and m.created_at >= cutoff
        ]

    def get_inner_state(self, user_id: UUID, character_id: str) -> Optional[InnerState]:
        """Return InnerState for a (user, character) pair."""
        return self._states.get(self._key(user_id, character_id))

    def get_context_block(
        self,
        user_id: UUID,
        character_id: str,
    ) -> Dict[str, Any]:
        """Return a context-block dict for the Composer hot path.

        Adapter that maps InnerState dataclass fields to the dict shape
        expected by ComposerService._build_inner_state_block.

        Returns:
            {
                "internal_monologue": str,
                "recent_reflections": [str, ...],
                "current_need": str,
            }
        """
        state = self.get_inner_state(user_id, character_id)
        if state is None:
            return {
                "internal_monologue": "",
                "recent_reflections": [],
                "current_need": "",
            }
        return {
            "internal_monologue": getattr(state, "internal_monologue", "") or "",
            "recent_reflections": list(getattr(state, "recent_reflections", []) or []),
            "current_need": getattr(state, "current_need", "") or "",
        }

    def run_seed_proactive_injection(
        self,
        user_id: UUID,
        character_id: str,
        *,
        num_messages: int = 3,
        base_date: Optional[datetime] = None,
    ) -> List[ProactiveMessage]:
        """Inject simulated proactive messages for seed data / demo scenarios.

        Used by seed_demo.py to pre-populate proactive history.
        """
        if base_date is None:
            base_date = datetime.now(timezone.utc)

        messages = []
        for i in range(num_messages):
            ts = base_date - timedelta(days=num_messages - i)
            templates = PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES["rin"])
            content = templates[i % len(templates)]
            msg = ProactiveMessage(
                user_id=user_id,
                character_id=character_id,
                content=content,
                trigger_type="scheduled",
                created_at=ts,
            )
            messages.append(msg)

        self._proactives.extend(messages)
        for m in messages:
            PROACTIVE_MESSAGES_TOTAL.labels(
                character=character_id, trigger_type=m.trigger_type
            ).inc()

        return messages
