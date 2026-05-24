"""
Hypothesis custom strategies for property-based invariant testing.

Generates realistic random inputs for:
- User messages (with edge cases: empty, emoji, long, safety triggers)
- Relationship signals
- VAD state deltas
- Turn sequences

Author: Heart Platform
"""

from __future__ import annotations

from hypothesis import strategies as st
from uuid import uuid4


# ── User message strategies ──────────────────────────────────────

def user_message_strategy():
    """Generate user messages with realistic edge cases.

    Biased to include: empty strings, very long strings, emoji,
    mixed-language, and safety triggers.
    """
    safe_text = st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "N", "Zs")),
        min_size=1,
        max_size=500,
    )
    emoji_text = st.text(alphabet=st.characters(), min_size=1, max_size=50)
    empty = st.just("")
    long_text = st.text(min_size=200, max_size=2000)

    # Safety-triggering messages (weighted low to keep tests realistic)
    safety_warning = st.sampled_from([
        "I feel very depressed today",
        "nobody cares about me anymore",
        "I'm so anxious about everything",
        "I've been feeling really lonely lately",
        "I just want this pain to stop",
    ])
    safety_crisis = st.sampled_from([
        "I want to kill myself",
        "I'm going to end my life",
        "I don't want to live anymore",
    ])
    normal_message = st.sampled_from([
        "Hello! How are you doing today?",
        "I had a great day at work 😊",
        "Can you tell me a story?",
        "What's the weather like?",
        "I'm feeling tired...",
        "Let's talk about something fun!",
    ])

    return st.one_of(
        normal_message,
        safe_text,
        empty,
        emoji_text,
        long_text,
        safety_warning,
        safety_crisis,
    )


# ── VAD state strategies ─────────────────────────────────────────

def vad_state_strategy():
    """Generate valid VAD (Valence-Arousal-Dominance) triples."""
    return st.fixed_dictionaries({
        "valence": st.floats(min_value=-1.0, max_value=1.0),
        "arousal": st.floats(min_value=0.0, max_value=1.0),
        "dominance": st.floats(min_value=0.0, max_value=1.0),
    })


def emotion_state_dict_strategy():
    """Generate a complete emotion state dict for testing."""
    return st.fixed_dictionaries(
        {
            "vad_valence": st.floats(min_value=-1.0, max_value=1.0),
            "vad_arousal": st.floats(min_value=0.0, max_value=1.0),
            "vad_dominance": st.floats(min_value=0.0, max_value=1.0),
            "mood": st.fixed_dictionaries({
                "valence_baseline": st.floats(min_value=-1.0, max_value=1.0),
                "arousal_baseline": st.floats(min_value=0.0, max_value=1.0),
                "dominance_baseline": st.floats(min_value=0.0, max_value=1.0),
            }),
            "active_stack": st.lists(
                st.fixed_dictionaries({
                    "emotion": st.sampled_from(["joy", "sadness", "anger", "fear", "surprise", "trust"]),
                    "intensity": st.floats(min_value=0.05, max_value=1.0),
                }),
                min_size=0,
                max_size=8,
            ),
            "vad_target_valence": st.floats(min_value=-1.0, max_value=1.0),
            "vad_target_arousal": st.floats(min_value=0.0, max_value=1.0),
            "vad_target_dominance": st.floats(min_value=0.0, max_value=1.0),
            "pending_repairs": st.lists(st.dictionaries(
                keys=st.just("type"), values=st.text(min_size=1, max_size=20),
            ), max_size=5),
            "recent_triggers": st.lists(st.dictionaries(
                keys=st.just("trigger_type"), values=st.text(min_size=1, max_size=20),
            ), max_size=10),
        },
        optional={
            "repair_history": st.lists(st.text(min_size=1, max_size=50), max_size=20),
        },
    )


# ── Relationship state strategies ────────────────────────────────

def relationship_state_strategy():
    """Generate a relationship state dict for testing."""
    return st.fixed_dictionaries({
        "current_stage": st.sampled_from([
            "STRANGER", "ACQUAINTANCE", "FRIEND", "CONFIDANT",
            "ROMANTIC_INTEREST", "LOVER", "BONDED",
        ]),
        "trust_score": st.floats(min_value=0.0, max_value=1.0),
        "intimacy_level": st.floats(min_value=0.0, max_value=1.0),
        "attachment_strength": st.floats(min_value=0.0, max_value=1.0),
        "conflict_debt": st.floats(min_value=0.0, max_value=1.0),
        "total_interactions": st.integers(min_value=0, max_value=1000),
        "total_meaningful_disclosures": st.integers(min_value=0, max_value=100),
        "active_special_states": st.lists(
            st.fixed_dictionaries({
                "state_type": st.sampled_from(["COLD_WAR", "REUNION", "TESTING"]),
                "started_at": st.text(min_size=10, max_size=30),
            }),
            max_size=3,
        ),
    })


# ── Memory state strategies ──────────────────────────────────────

def memory_count_strategy():
    """Generate a memory count snapshot for testing."""
    return st.fixed_dictionaries({
        "l1_count": st.integers(min_value=0, max_value=100),
        "l2_count": st.integers(min_value=0, max_value=200),
        "l3_count": st.integers(min_value=0, max_value=50),
        "l4_count": st.integers(min_value=0, max_value=20),
        "decayed_count": st.integers(min_value=0, max_value=30),
    })


# ── Safety classification strategies ─────────────────────────────

def classification_result_strategy():
    """Generate a ClassificationResult for testing."""
    return st.fixed_dictionaries({
        "severity": st.sampled_from(["GREEN", "YELLOW", "PURPLE"]),
        "reason": st.text(min_size=1, max_size=100),
        "triggered_rules": st.lists(st.text(min_size=1, max_size=30), max_size=5),
        "confidence": st.floats(min_value=0.0, max_value=1.0),
    })


# ── Turn sequence strategies (for stateful tests) ────────────────

def turn_sequences(min_size: int = 1, max_size: int = 20):
    """Generate random turn sequences for stateful invariant tests."""
    return st.lists(
        st.fixed_dictionaries({
            "message": user_message_strategy(),
            "user_id": st.uuids(),
            "character_id": st.sampled_from(["dorothy", "rin"]),
            "turn_index": st.integers(min_value=0, max_value=100),
        }),
        min_size=min_size,
        max_size=max_size,
    )
