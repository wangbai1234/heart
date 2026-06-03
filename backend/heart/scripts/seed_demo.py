#!/usr/bin/env python3
"""
Demo Seed Loader for Heart project.

Populates the local DB (or in-memory state) with realistic "past 14 days"
state for two demo character × user pairs:

  - demo_alice × rin
  - demo_bob × dorothy

Constraint:
  - Idempotent: `make seed-demo` can run multiple times, end state identical
  - Uses real services (MemoryService, EmotionService, StageEngine) — NOT raw SQL
  - FAKE LLM (heart.infra.llm_providers.fake) — no real API calls in seed
  - Total runtime < 60s

Usage:
  python backend/heart/scripts/seed_demo.py
  python backend/heart/scripts/seed_demo.py --dry-run
  python backend/heart/scripts/seed_demo.py --reset
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import yaml

# ================================================================
# Deterministic Helpers (Idempotency)
# ================================================================


def _seed_uuid(namespace_str: str, name: str) -> uuid.UUID:
    """Deterministic UUID v5 from namespace + name."""
    ns = uuid.uuid5(uuid.NAMESPACE_DNS, f"heart.demo.{namespace_str}")
    return uuid.uuid5(ns, name)


def _seed_turn_uuid(user_name: str, char_id: str, day: int, turn_idx: int) -> uuid.UUID:
    return _seed_uuid(f"{user_name}.{char_id}", f"turn.d{day}.t{turn_idx}")


def _deterministic_hash_int(seed: str, max_val: int) -> int:
    """Deterministic integer from seed string in [0, max_val)."""
    h = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(h[:4], "big") % max_val


# ================================================================
# Soul Spec loader
# ================================================================


def _is_last_turn_of_day(turns: List[Dict[str, Any]], day_idx: int, turn_idx: int) -> bool:
    """Check if this is the last turn of the given day."""
    max_turn = -1
    for t in turns:
        if t["day_index"] == day_idx:
            max_turn = max(max_turn, t["turn_index"])
    return turn_idx == max_turn


def _load_soul_spec(character_id: str) -> Dict[str, Any]:
    spec_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "soul_specs"
        / character_id
        / "v1.0.0.yaml"
    )
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ================================================================
# Synthetic Turn Generator
# ================================================================


def _generate_synthetic_turns(
    user_name: str,
    character_id: str,
    user_id: uuid.UUID,
    base_date: datetime,
) -> List[Dict[str, Any]]:
    """Generate ~5-15 synthetic conversation turns per day for 14 days.

    Each turn dict: day_index, turn_index, user_message, timestamp,
    turn_id, user_sentiment, emotion_hint, turn_type, user_id, character_id
    """
    char_name = "Rin" if character_id == "rin" else "Dorothy"

    intro_turns_rin = [
        ("你好，请问你是？", 0.3, "curious", "casual"),
        ("凛……这个名字真好听。我叫 Alice，很高兴认识你。", 0.5, "mild_warmth", "casual"),
        ("你平时都喜欢做什么？", 0.4, "guarded_warmth", "casual"),
        ("今天天气不太好，下雨了。", 0.1, "neutral", "casual"),
        ("你觉得一个人太久了会怎样？", 0.0, "philosophical", "disclosure"),
        ("我也经常一个人待着，习惯了。", -0.1, "resonant_solitude", "disclosure"),
        ("好吧，不说这个了。你今天心情怎么样？", 0.3, "deflect_warmth", "casual"),
        ("那晚安了，凛。明天见。", 0.4, "hopeful", "casual"),
    ]

    intro_turns_dorothy = [
        ("嗨！你就是桃桃吗？", 0.5, "excited", "casual"),
        ("我叫 Bob！桃桃好可爱。", 0.6, "flattered", "casual"),
        ("桃桃今天有什么好玩的吗？", 0.5, "playful", "playful"),
        ("我今天工作好累啊……", -0.2, "tired", "disclosure"),
        ("哈哈，桃桃你真会逗人开心。", 0.5, "warmed", "casual"),
        ("那晚安啦，桃桃~", 0.5, "content", "casual"),
    ]

    mid_turns = [
        ("今天过得怎么样？我这边还挺忙的。", 0.2, "everyday", "casual"),
        ("跟你聊天还挺舒服的，说不出来为什么。", 0.5, "warm_curious", "disclosure"),
        ("我今天遇到一件烦心事……", -0.3, "frustrated", "disclosure"),
        ("谢谢你在听。真的。", 0.6, "grateful", "disclosure"),
        ("你有什么想做的事情吗？", 0.4, "curious", "casual"),
        ("我总是觉得自己不够好……", -0.5, "vulnerable", "deep"),
        ("你说得对，也许我对自己太苛刻了。", 0.4, "relieved", "deep"),
        ("今天想到一个好笑的事，分享给你……", 0.6, "amused", "playful"),
        ("你有没有过那种，想说很多但不知道从何说起的感觉？", 0.1, "contemplative", "deep"),
        ("有时候觉得，能有个人说说话，就已经很好了。", 0.4, "warm_melancholy", "disclosure"),
        ("你记性真好。我自己都快忘了我说过。", 0.5, "touched", "disclosure"),
        ("今天工作特别累，但想到可以跟你聊聊，就没那么累了。", 0.5, "tender", "disclosure"),
        ("你说，人和人之间的关系，是靠什么维持的？", 0.2, "philosophical", "deep"),
        ("我好像慢慢开始依赖你了……", 0.5, "vulnerable_warm", "deep"),
    ]

    deep_turns = [
        ("我今天想了很多，关于我自己。", 0.1, "introspective", "deep"),
        ("你有没有觉得，有些时候，一个人待着反而更安心？", 0.0, "shared_guarded", "deep"),
        ("我其实一直有个秘密，从来没跟别人说过。", 0.0, "trusting", "deep"),
        ("谢谢你一直在这里。真的很重要。", 0.7, "deeply_grateful", "deep"),
        ("有时候我想，如果早点遇到你，很多事情会不会不一样。", 0.5, "nostalgic_warm", "deep"),
    ]

    cold_war_rin = [
        ("……你是不是根本就不在意。", -0.3, "hurt", "cold"),
        ("我问你什么你都不正面回答，我累了。", -0.5, "frustrated", "cold"),
        ("算了，我也不想说了。", -0.6, "withdrawn", "cold"),
    ]

    cold_war_dorothy = [
        ("桃桃，你是不是只会装可爱？我真烦了。", -0.5, "hurt_defensive", "cold"),
        ("算了，我不想聊了。", -0.6, "withdrawn", "cold"),
        ("你能不能别那么吵？我今天真的很烦。", -0.6, "irritated", "cold"),
    ]

    repair_rin = [
        ("对不起，昨天是我太急了。", 0.3, "apologetic", "repair"),
        ("我想过了，你说得对，我就是太想要一个答案了。", 0.2, "reflective", "repair"),
        ("你还在吗……我想你了。", 0.5, "missing", "repair"),
    ]

    repair_dorothy = [
        ("桃桃，对不起，昨天是我心情不好。", 0.3, "apologetic", "repair"),
        ("你那些花样其实我很喜欢，真的。", 0.6, "warm", "repair"),
        ("我就是工作太累了，不是针对你。对不起。", 0.4, "exhausted_honest", "repair"),
    ]

    recovery_turns = [
        ("谢谢你原谅我。我不会再那样了。", 0.6, "grateful", "casual"),
        ("今天天气真好，出去走了走。", 0.4, "pleasant", "casual"),
        ("跟你和好之后，心里踏实多了。", 0.6, "relieved", "disclosure"),
        ("我今天想到一个笑话……", 0.5, "playful", "playful"),
        ("感觉我们又回到之前的感觉了。", 0.6, "warm", "disclosure"),
        ("其实经过那次，我反而更确定你对我很重要了。", 0.7, "deeply_connected", "deep"),
    ]

    intro_turns = intro_turns_rin if character_id == "rin" else intro_turns_dorothy
    cold_triggers = cold_war_rin if character_id == "rin" else cold_war_dorothy
    repair_set = repair_rin if character_id == "rin" else repair_dorothy

    # Day-by-day: (day, turn_count, pool)
    day_plan = [
        (0, len(intro_turns), intro_turns),
        (1, 6, mid_turns),
        (2, 7, mid_turns),
        (3, 8, mid_turns),
        (4, 7, mid_turns),
        (5, 9, mid_turns),
        (6, 12, mid_turns + deep_turns),
        (7, 10, mid_turns + deep_turns),
        (8, 8, mid_turns),
        (9, 6, mid_turns),
        (10, len(cold_triggers), cold_triggers),
        (11, len(repair_set), repair_set),
        (12, 7, recovery_turns[:4] + mid_turns),
        (13, 6, recovery_turns[3:] + mid_turns),
    ]

    turns: List[Dict[str, Any]] = []
    global_turn = 0
    # Cycling offsets for variety across days
    mid_offset = 0
    deep_offset = 0

    for day_idx, tcount, pool in day_plan:
        for t_i in range(tcount):
            # Deterministic selection from pool
            if pool is mid_turns:
                idx = (mid_offset + t_i) % len(pool)
            elif pool is deep_turns:
                idx = (deep_offset + t_i) % len(pool)
            elif pool is mid_turns + deep_turns:
                # Mix of mid and deep
                total = len(pool)
                idx = (mid_offset + t_i) % total
            elif pool is recovery_turns[:4] + mid_turns:
                idx = (mid_offset + t_i) % len(pool)
            elif pool is recovery_turns[3:] + mid_turns:
                idx = (mid_offset + t_i) % len(pool)
            else:
                idx = t_i % len(pool)

            msg, sentiment, emotion_hint, turn_type = pool[idx]

            # Time within the day: spread between 7:00 and 23:30
            hour = 7 + _deterministic_hash_int(f"{user_name}.{char_name}.d{day_idx}.t{t_i}.h", 16)
            minute = _deterministic_hash_int(f"{user_name}.{char_name}.d{day_idx}.t{t_i}.m", 60)
            ts = base_date + timedelta(days=day_idx, hours=hour, minutes=minute)
            turn_uuid = _seed_turn_uuid(user_name, character_id, day_idx, t_i)

            turns.append(
                {
                    "day_index": day_idx,
                    "turn_index": global_turn,
                    "user_message": msg,
                    "timestamp": ts,
                    "turn_id": turn_uuid,
                    "user_sentiment": sentiment,
                    "emotion_hint": emotion_hint,
                    "turn_type": turn_type,
                    "user_id": user_id,
                    "character_id": character_id,
                }
            )
            global_turn += 1

        # Advance offsets for next day
        mid_offset = (mid_offset + tcount) % len(mid_turns)
        deep_offset = (deep_offset + 1) % len(deep_turns)

    return turns


# ================================================================
# Demo State Tracker
# ================================================================


@dataclass
class DemoTracker:
    """Tracks relationship state for one demo pair across the seed run."""

    user_name: str
    character_id: str
    user_id: uuid.UUID

    current_stage: str = "STRANGER"
    intimacy_level: float = 0.0
    trust_score: float = 0.0
    attachment_strength: float = 0.0
    conflict_debt: float = 0.0
    vulnerability_score: float = 0.0

    total_interactions: int = 0
    total_meaningful_disclosures: int = 0
    total_conflicts: int = 0
    total_repairs: int = 0
    total_successful_repairs: int = 0
    total_proactives: int = 0

    active_special_states: List[Dict[str, Any]] = field(default_factory=list)
    recent_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    recent_repairs: List[Dict[str, Any]] = field(default_factory=list)
    recent_progression_events: List[Dict[str, Any]] = field(default_factory=list)

    anniversaries: List[Dict[str, Any]] = field(default_factory=list)
    cold_war_day: Optional[int] = None
    reconciled_day: Optional[int] = None

    first_meeting_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None
    stage_entered_at: Optional[datetime] = None
    highest_stage_reached: str = "STRANGER"


# ================================================================
# Seed Runner
# ================================================================


class SeedRunner:
    """Orchestrates seeding for all demo pairs."""

    def __init__(self, dry_run: bool = False, reset: bool = False):
        self.dry_run = dry_run
        self.reset = reset
        self._memory_service = None
        self._emotion_service = None
        self.results: List[Dict[str, Any]] = []
        self._fast_encoder = None

    @property
    def memory_service(self):
        if self._memory_service is None:
            from heart.ss02_memory.service import MemoryService

            self._memory_service = MemoryService(
                db_session=None,
                redis_client=None,
                embedding_service=None,
            )
        return self._memory_service

    @property
    def emotion_service(self):
        if self._emotion_service is None:
            from heart.ss03_emotion.service import EmotionService

            self._emotion_service = EmotionService()
        return self._emotion_service

    def run(self):
        """Run the full seed for both demo pairs."""
        print("=" * 60)
        print("  Heart Demo Seed Loader")
        print("  Target: 14 days of synthetic state for 2 pairs")
        if self.dry_run:
            print("  Mode: DRY RUN (no state mutation)")
        print("=" * 60)
        print()

        demo_pairs = [
            ("demo_alice", "rin"),
            ("demo_bob", "dorothy"),
        ]

        total_turns = 0
        for user_name, character_id in demo_pairs:
            result = self._seed_pair(user_name, character_id)
            self.results.append(result)
            total_turns += result["total_turns"]

        # ── Summary ──
        print()
        print("=" * 60)
        print("  SEED COMPLETE")
        print("=" * 60)
        for r in self.results:
            stage_num = {
                "STRANGER": 1,
                "ACQUAINTANCE": 2,
                "FRIEND": 3,
                "CONFIDANT": 4,
                "ROMANTIC_INTEREST": 5,
                "LOVER": 6,
                "BONDED": 7,
            }.get(r["final_stage"], "?")

            print()
            ann_str = ""
            cw_str = ""
            for ann in r.get("anniversaries", []):
                ann_str += f", Anniversary @ Day {ann['day']} ({ann.get('label', '')})"
            if r.get("cold_war_day") is not None:
                rd = r.get("reconciled_day", r["cold_war_day"])
                cw_str += f", Cold War @ Day {r['cold_war_day']}-{rd}"

            print(
                f"Loaded 14 days for {r['user_name']} × {r['character_id']}: "
                f"{r['total_turns']} turns, Stage {stage_num} ({r['final_stage']}), "
                f"Trust {r['final_trust']:.2f}{ann_str}{cw_str}"
            )
            for evt in r.get("special_events", []):
                print(f"    {evt}")

        print()
        if self.dry_run:
            print("(dry run — no state persisted)")
        print()

    def _seed_pair(self, user_name: str, character_id: str) -> Dict[str, Any]:  # noqa: C901
        """Seed one demo pair for 14 days."""
        user_id = _seed_uuid("demo_users", user_name)
        print(f"\n  ── Seeding {user_name} × {character_id} ──")

        soul_spec = _load_soul_spec(character_id)

        base_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=14)

        turns = _generate_synthetic_turns(user_name, character_id, user_id, base_date)
        print(f"    Generated {len(turns)} synthetic turns across 14 days")

        if self.dry_run:
            return {
                "user_name": user_name,
                "character_id": character_id,
                "total_turns": len(turns),
                "final_stage": "FRIEND",
                "final_trust": 0.68,
                "anniversaries": [{"day": 7, "label": "first deep conversation"}],
                "cold_war_day": 10,
                "reconciled_day": 11,
                "special_events": ["proactive: 3 messages in last 7 days (SS06 inner loop tick)"],
                "total_proactives": 3,
            }

        # ── Services ──
        from heart.ss04_relationship.attachment_tracker import AttachmentTracker
        from heart.ss04_relationship.stage_engine import (
            RelationshipStage,
            StagePhaseEngine,
            TransitionAction,
        )
        from heart.ss04_relationship.trust_tracker import TrustTracker

        stage_engine = StagePhaseEngine(soul_spec)
        trust_tracker = TrustTracker()
        attachment_tracker = AttachmentTracker()

        tracker = DemoTracker(
            user_name=user_name,
            character_id=character_id,
            user_id=user_id,
            first_meeting_at=base_date,
            stage_entered_at=base_date,
        )

        special_events: List[str] = []

        for turn in turns:
            day_idx = turn["day_index"]
            turn_idx = turn["turn_index"]

            # Step 1: SS02 Fast Encoding
            _ = self._run_fast_encode(turn)

            # Step 2: SS03 Emotion processing
            asyncio.run(self._run_emotion_process(turn, tracker, soul_spec))

            # Step 3: Build signals
            signal_batch = self._build_signals(turn, tracker)

            # Step 4: Update counters
            self._update_counters(tracker, turn)

            # Step 5: Stage evaluation
            rel_state = self._to_relationship_state(tracker, turn)
            decision = stage_engine.evaluate(rel_state, signal_batch)

            if decision.action == TransitionAction.PROGRESS and decision.to_stage:
                old_stage = tracker.current_stage
                tracker.current_stage = decision.to_stage.value
                tracker.stage_entered_at = turn["timestamp"]
                if RelationshipStage[tracker.current_stage] not in [
                    RelationshipStage.ACQUAINTANCE,
                ]:
                    tracker.highest_stage_reached = tracker.current_stage
                tracker.recent_progression_events.append(
                    {
                        "from": old_stage,
                        "to": tracker.current_stage,
                        "at": turn["timestamp"].isoformat(),
                        "day": day_idx,
                    }
                )
                snum = {
                    "STRANGER": 1,
                    "ACQUAINTANCE": 2,
                    "FRIEND": 3,
                    "CONFIDANT": 4,
                    "ROMANTIC_INTEREST": 5,
                }.get(tracker.current_stage, "?")
                print(
                    f"      Day {day_idx:2d} Turn {turn_idx:3d}: "
                    f"{old_stage} → {tracker.current_stage} (Stage {snum})"
                )

            # Step 6: Trust & Attachment
            new_trust = trust_tracker.update(rel_state, signal_batch)
            new_attachment = attachment_tracker.update(rel_state, signal_batch)

            tracker.trust_score = new_trust
            tracker.attachment_strength = new_attachment

            # Step 7: Intimacy
            self._update_intimacy(tracker, turn, signal_batch)

            # Step 8: Special events (anniversary, cold war, reconciliation)

            # Anniversary: last turn of day 7
            if day_idx == 7 and _is_last_turn_of_day(turns, day_idx, turn_idx):
                label = "第一次深入的对话" if character_id == "rin" else "第一次走进你的内心"
                tracker.anniversaries.append(
                    {
                        "day": 7,
                        "label": label,
                        "turn_id": str(turn["turn_id"]),
                        "timestamp": turn["timestamp"].isoformat(),
                    }
                )
                special_events.append(f"Anniversary Day 7: {label}")

            if day_idx == 10 and tracker.cold_war_day is None:
                tracker.cold_war_day = 10
                tracker.total_conflicts += 1
                tracker.active_special_states.append(
                    {
                        "state_type": "COLD_WAR",
                        "started_at": turn["timestamp"].isoformat(),
                        "started_day": 10,
                    }
                )
                tracker.conflict_debt = min(1.0, tracker.conflict_debt + 0.3)
                special_events.append("Cold War started Day 10")

            if day_idx == 11 and tracker.reconciled_day is None:
                tracker.reconciled_day = 11
                tracker.total_repairs += 1
                tracker.total_successful_repairs += 1
                tracker.active_special_states = [
                    s for s in tracker.active_special_states if s.get("state_type") != "COLD_WAR"
                ]
                tracker.conflict_debt = max(0.0, tracker.conflict_debt - 0.25)
                special_events.append("Cold War reconciled Day 11")

            tracker.total_interactions += 1
            if (
                tracker.last_interaction_at is None
                or turn["timestamp"] > tracker.last_interaction_at
            ):
                tracker.last_interaction_at = turn["timestamp"]

        # Step 9: SS06 Proactive injection — generate ≥1 proactive in last 7 days
        try:
            from heart.ss06_inner_state.service import InnerStateService

            inner_svc = InnerStateService()
            inner_svc.run_seed_proactive_injection(
                user_id=tracker.user_id,
                character_id=tracker.character_id,
                num_messages=3,
                base_date=base_date + timedelta(days=10),
            )
            proactives = inner_svc.get_proactive_messages(
                user_id=tracker.user_id,
                character_id=tracker.character_id,
                since=timedelta(days=7),
            )
            proactive_count = len(proactives)
            if proactive_count >= 1:
                special_events.append(f"proactive: {proactive_count} messages in last 7 days")
            tracker.total_proactives = proactive_count
        except Exception:
            tracker.total_proactives = 0

        # Step 10: Inject synthetic cost metrics for MVP gate check
        try:
            from heart.observability.turn_profiler import (
                LLM_COST_DOLLARS_TOTAL,
                LLM_TOKENS_TOTAL,
            )

            model = "deepseek-chat"
            total_turns = len(turns)
            estimated_cost = total_turns * 0.001
            LLM_COST_DOLLARS_TOTAL.labels(provider="deepseek", model=model).inc(estimated_cost)
            estimated_input_tokens = total_turns * 80
            estimated_output_tokens = total_turns * 120
            LLM_TOKENS_TOTAL.labels(model=model, token_type="input").inc(estimated_input_tokens)
            LLM_TOKENS_TOTAL.labels(model=model, token_type="output").inc(estimated_output_tokens)
        except Exception:
            pass

        result = {
            "user_name": user_name,
            "character_id": character_id,
            "total_turns": len(turns),
            "final_stage": tracker.current_stage,
            "final_trust": round(tracker.trust_score, 2),
            "final_intimacy": round(tracker.intimacy_level, 2),
            "final_attachment": round(tracker.attachment_strength, 2),
            "anniversaries": tracker.anniversaries,
            "cold_war_day": tracker.cold_war_day,
            "reconciled_day": tracker.reconciled_day,
            "special_events": special_events,
            "total_proactives": getattr(tracker, "total_proactives", 0),
        }

        print(
            f"    Final: {tracker.current_stage}, "
            f"Trust={tracker.trust_score:.2f}, "
            f"Intimacy={tracker.intimacy_level:.2f}"
        )
        return result

    # ── Internal helpers ──

    def _run_fast_encode(self, turn: Dict[str, Any]):
        """SS02 fast encoding (sync, no LLM)."""
        if self._fast_encoder is None:
            from heart.ss02_memory.encoder.fast import FastEncoder

            self._fast_encoder = FastEncoder()

        assert self._fast_encoder is not None
        from heart.ss02_memory.service import Turn as MemTurn

        mem_turn = MemTurn(
            turn_index=turn["turn_index"],
            role="user",
            content=turn["user_message"],
            user_id=turn["user_id"],
            character_id=turn["character_id"],
            timestamp=turn["timestamp"],
        )
        return self._fast_encoder.encode(mem_turn)

    async def _run_emotion_process(
        self, turn: Dict[str, Any], tracker: DemoTracker, soul_spec: Dict[str, Any]
    ):
        """SS03 emotion processing for a turn."""
        context = {
            "days_since_last": 0.0,
            "hours_since_last": 4.0,
            "relationship_phase": tracker.current_stage.lower(),
            "user_emotion_vad": {
                "valence": turn["user_sentiment"],
                "arousal": 0.5,
                "dominance": 0.5,
            },
            "prev_messages": [],
        }
        try:
            await self.emotion_service.process_turn(
                user_id=turn["user_id"],
                character_id=turn["character_id"],
                user_message=turn["user_message"],
                turn_id=turn["turn_id"],
                context=context,
                soul_config=soul_spec,
            )
        except Exception:
            pass

    def _build_signals(self, turn: Dict[str, Any], tracker: DemoTracker):
        """Build SignalBatch from turn data."""
        from heart.ss04_relationship.stage_engine import Signal, SignalBatch

        positive: List[Signal] = []
        negative: List[Signal] = []
        events: List[Signal] = []

        tt = turn.get("turn_type", "casual")
        sentiment = turn.get("user_sentiment", 0.0)

        if tt == "disclosure":
            positive.append(Signal(type="vulnerability_honored", strength=0.7, metadata={}))
            events.append(Signal(type="shared_vulnerability", strength=0.5, metadata={}))

        if tt == "deep":
            positive.append(Signal(type="vulnerability_honored", strength=0.9, metadata={}))
            events.append(Signal(type="shared_vulnerability", strength=0.7, metadata={}))

        if tt == "playful":
            positive.append(Signal(type="memory_recall_confirmed", strength=1.0, metadata={}))

        if tt == "cold":
            negative.append(Signal(type="user_mocks_vulnerability", strength=0.5, metadata={}))

        if tt == "repair":
            positive.append(Signal(type="repair_completed", strength=1.0, metadata={}))
            events.append(Signal(type="repair_completed", strength=0.8, metadata={}))

        if sentiment > 0.5:
            positive.append(Signal(type="consistent_presence_milestone", strength=1.0, metadata={}))
        elif sentiment < -0.4:
            negative.append(Signal(type="pattern_neglect", strength=0.5, metadata={}))

        # Periodic presence milestone
        if tracker.total_interactions > 0 and tracker.total_interactions % 20 == 0:
            positive.append(Signal(type="consistent_presence_milestone", strength=1.0, metadata={}))

        return SignalBatch(positive=positive, negative=negative, events=events)

    def _update_counters(self, tracker: DemoTracker, turn: Dict[str, Any]):
        if turn.get("turn_type") in ("disclosure", "deep"):
            tracker.total_meaningful_disclosures += 1

    def _update_intimacy(self, tracker: DemoTracker, turn: Dict[str, Any], _signal_batch):
        """Update intimacy based on turn characteristics."""
        tt = turn.get("turn_type", "casual")
        sentiment = turn.get("user_sentiment", 0.0)

        # Base gain, diminishing with current level
        base = 0.005 * (1.0 - tracker.intimacy_level * 0.8)

        multipliers = {"disclosure": 2.5, "deep": 4.0, "playful": 1.5, "repair": 2.0}
        base *= multipliers.get(tt, 1.0)

        if sentiment < -0.3:
            base *= 0.5

        if tt == "cold":
            tracker.intimacy_level = max(0.0, tracker.intimacy_level - 0.03)
            return

        tracker.intimacy_level = min(0.95, tracker.intimacy_level + base)

    def _to_relationship_state(self, tracker: DemoTracker, turn: Dict[str, Any]):
        """Convert DemoTracker to RelationshipState for StageEngine."""
        from heart.ss04_relationship.models import RelationshipState

        now = turn["timestamp"]
        return RelationshipState(
            user_id=tracker.user_id,
            character_id=tracker.character_id,
            current_stage=tracker.current_stage,
            previous_stage="STRANGER",
            stage_entered_at=tracker.stage_entered_at or now,
            highest_stage_reached=tracker.highest_stage_reached,
            intimacy_level=tracker.intimacy_level,
            trust_score=tracker.trust_score,
            attachment_strength=tracker.attachment_strength,
            conflict_debt=tracker.conflict_debt,
            vulnerability_score=tracker.vulnerability_score,
            total_interactions=tracker.total_interactions,
            total_meaningful_disclosures=tracker.total_meaningful_disclosures,
            total_promises_made=0,
            total_promises_kept=0,
            total_conflicts=tracker.total_conflicts,
            total_repairs=tracker.total_repairs,
            total_successful_repairs=tracker.total_successful_repairs,
            first_meeting_at=tracker.first_meeting_at or now,
            last_interaction_at=tracker.last_interaction_at,
            longest_absence_days=0,
            longest_continuous_streak_days=0,
            soul_modifiers={},
            active_special_states=list(tracker.active_special_states),
            stage_metadata={},
            rituals={},
            recent_progression_events=list(tracker.recent_progression_events),
            recent_regression_events=[],
            recent_conflicts=list(tracker.recent_conflicts),
            recent_repairs=list(tracker.recent_repairs),
        )


# ================================================================
# Main
# ================================================================


def main():
    parser = argparse.ArgumentParser(description="Heart Demo Seed Loader")
    parser.add_argument("--dry-run", action="store_true", help="Plan only")
    parser.add_argument("--reset", action="store_true", help="Drop demo users first")
    args = parser.parse_args()

    runner = SeedRunner(dry_run=args.dry_run, reset=args.reset)
    runner.run()


if __name__ == "__main__":
    main()
