"""
Unit tests for Memory Reconstructor - SS02 §3.9 + §6.7

Coverage:
- All 5 states × 2 characters (Rin + Dorothy)
- Critical: Rin's "……" in fading/faint
- Critical: Dorothy's "诶嘿嘿" + 语气词
- Anti-pattern violations
- Length clamping

Author: 心屿团队
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import yaml

from heart.ss02_memory.models import EpisodicMemory, FactNode, IdentityMemory
from heart.ss02_memory.reconstructor import Reconstructor
from heart.ss02_memory.retriever.base import ScoredMemory


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def character_id_rin():
    return "rin"


@pytest.fixture
def character_id_dorothy():
    return "dorothy"


@pytest.fixture
def rin_soul_spec():
    """Load Rin soul spec (subset for testing)."""
    return {
        "character_id": "rin",
        "voice_dna": [
            {
                "id": "vd-001",
                "pattern": "使用……表示思考、停顿",
                "frequency": "high",
            },
            {
                "id": "vd-NEW-C",
                "pattern": "回避「我们」",
                "frequency": "medium",
            },
        ],
        "anti_patterns": {
            "hard_never": [
                "宝贝",
                "亲爱的",
                "嘤嘤嘤",
                "好~的~呀~",
                "你真可爱",
            ],
            "forbidden_patterns": [
                {"regex": r"[!！]{2,}", "description": "连续两个感叹号"},
                {"regex": r"~", "description": "波浪号"},
            ],
        },
    }


@pytest.fixture
def dorothy_soul_spec():
    """Load Dorothy soul spec (subset for testing)."""
    return {
        "character_id": "dorothy",
        "voice_dna": [
            {
                "id": "vd-DOROTHY-001",
                "pattern": "桃桃自称",
                "frequency": "very_high",
            },
            {
                "id": "vd-DOROTHY-002",
                "pattern": "拟声词 + 句末语气词",
                "frequency": "very_high",
            },
        ],
        "anti_patterns": {
            "hard_never": [
                "无聊",
                "随便",
                "算了",
                "……",  # Dorothy FORBIDS ellipsis
            ],
            "forbidden_patterns": [
                {"regex": r"(……|\.{3,})", "description": "省略号"},
            ],
        },
    }


@pytest.fixture
def l2_memory_vivid(user_id):
    """L2 episodic memory in vivid state."""
    return EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id="rin",
        episode_summary="用户养了一只叫老铁的黑猫，怕雷。",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
        episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
        emotional_peak={"valence": 0.4, "arousal": 0.5, "label": "fond"},
        emotional_end={"valence": 0.3, "arousal": 0.4, "label": "calm"},
        emotional_significance=0.6,
        importance_score=0.8,
        initial_importance=0.8,
        decay_immunity=0.0,
        state="vivid",
        recall_count=0,
        reinforcement_history=[],
        linked_episodes=[],
        linked_facts=[],
        reconstruction_hints={},
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(hours=24),
        updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
    )


@pytest.fixture
def l2_memory_fading(user_id):
    """L2 episodic memory in fading state."""
    mem = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id="rin",
        episode_summary="用户的猫老铁",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=datetime.now(timezone.utc) - timedelta(days=7),
        episode_end_at=datetime.now(timezone.utc) - timedelta(days=7),
        emotional_peak={"valence": 0.3, "arousal": 0.4},
        emotional_end={"valence": 0.3, "arousal": 0.3},
        emotional_significance=0.5,
        importance_score=0.5,
        initial_importance=0.7,
        decay_immunity=0.0,
        state="fading",
        recall_count=1,
        reinforcement_history=[],
        linked_episodes=[],
        linked_facts=[],
        reconstruction_hints={},
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=7),
        updated_at=datetime.now(timezone.utc) - timedelta(days=7),
    )
    return mem


@pytest.fixture
def l2_memory_faint(user_id):
    """L2 episodic memory in faint state."""
    mem = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id="rin",
        episode_summary="用户的猫",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=datetime.now(timezone.utc) - timedelta(days=30),
        episode_end_at=datetime.now(timezone.utc) - timedelta(days=30),
        emotional_peak={"valence": 0.2, "arousal": 0.3},
        emotional_end={"valence": 0.2, "arousal": 0.2},
        emotional_significance=0.4,
        importance_score=0.3,
        initial_importance=0.6,
        decay_immunity=0.0,
        state="faint",
        recall_count=0,
        reinforcement_history=[],
        linked_episodes=[],
        linked_facts=[],
        reconstruction_hints={},
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
        updated_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    return mem


@pytest.fixture
def l2_memory_dormant(user_id):
    """L2 episodic memory in dormant state."""
    mem = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id="rin",
        episode_summary="用户的猫怕雷",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=datetime.now(timezone.utc) - timedelta(days=60),
        episode_end_at=datetime.now(timezone.utc) - timedelta(days=60),
        emotional_peak={"valence": 0.1, "arousal": 0.2},
        emotional_end={"valence": 0.1, "arousal": 0.1},
        emotional_significance=0.3,
        importance_score=0.15,
        initial_importance=0.5,
        decay_immunity=0.0,
        state="dormant",
        recall_count=0,
        reinforcement_history=[],
        linked_episodes=[],
        linked_facts=[],
        reconstruction_hints={},
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=60),
        updated_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    return mem


@pytest.fixture
def l2_memory_archived(user_id):
    """L2 episodic memory in archived state."""
    mem = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id="rin",
        episode_summary="用户养猫",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=datetime.now(timezone.utc) - timedelta(days=90),
        episode_end_at=datetime.now(timezone.utc) - timedelta(days=90),
        emotional_peak={"valence": 0.0, "arousal": 0.1},
        emotional_end={"valence": 0.0, "arousal": 0.0},
        emotional_significance=0.2,
        importance_score=0.05,
        initial_importance=0.4,
        decay_immunity=0.0,
        state="archived",
        recall_count=0,
        reinforcement_history=[],
        linked_episodes=[],
        linked_facts=[],
        reconstruction_hints={},
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=90),
        updated_at=datetime.now(timezone.utc) - timedelta(days=90),
        archived_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    return mem


@pytest.fixture
def l4_memory(user_id):
    """L4 identity memory (always vivid)."""
    return IdentityMemory(
        id=uuid4(),
        user_id=user_id,
        character_id="rin",
        category="foundational",
        key="user_name",
        value="小明",
        disclosed_at=datetime.now(timezone.utc) - timedelta(days=30),
        disclosure_context="first meeting",
        source_turn_ids=[uuid4()],
        sacred_reason="user's primary identifier",
        significance_score=0.95,
        promotion_trigger="first_disclosure",
        reconstruction_hints={},
        audit_log=[],
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
    )


# ============================================================
# Test Rin × 5 states
# ============================================================


class TestRinReconstruction:
    """Test Rin reconstruction across all 5 states."""

    def test_rin_vivid_state(self, l2_memory_vivid, rin_soul_spec):
        """Vivid state: full content, no hedge."""
        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_vivid,
            memory_id=l2_memory_vivid.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should contain core content
        assert "老铁" in result
        assert "黑猫" in result or "猫" in result
        # Vivid: no hedge
        assert "……" not in result or result.count("……") == 0  # no ellipsis in vivid

    def test_rin_fading_state_with_ellipsis(self, l2_memory_fading, rin_soul_spec):
        """CRITICAL: Fading state must have Rin's ellipsis ……"""
        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_fading,
            memory_id=l2_memory_fading.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.6},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # CRITICAL: Must have ellipsis
        assert "……" in result, f"Rin fading state must have ellipsis, got: {result}"
        # Should have hedge (好像 or ……)
        assert "猫" in result or "老铁" in result

    def test_rin_faint_state_with_ellipsis(self, l2_memory_faint, rin_soul_spec):
        """CRITICAL: Faint state must have Rin's ellipsis ……"""
        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_faint,
            memory_id=l2_memory_faint.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.4},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # CRITICAL: Must have ellipsis
        assert "……" in result, f"Rin faint state must have ellipsis, got: {result}"
        # Fragmentary content
        assert "猫" in result

    def test_rin_dormant_state(self, l2_memory_dormant, rin_soul_spec):
        """Dormant state: emergence marker."""
        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_dormant,
            memory_id=l2_memory_dormant.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.3},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should have emergence marker (……等等 or similar)
        assert "……" in result
        assert "猫" in result or "怕雷" in result

    def test_rin_archived_state(self, l2_memory_archived, rin_soul_spec):
        """Archived state: disorientation marker."""
        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_archived,
            memory_id=l2_memory_archived.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.2},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should have disorientation
        assert "……" in result
        assert len(result) > 0

    def test_rin_l4_always_vivid(self, l4_memory, rin_soul_spec):
        """L4 memories are always vivid, no hedging."""
        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l4_memory,
            memory_id=l4_memory.id,
            memory_type="L4",
            score_breakdown={"importance": 1.0},
            retrieved_by=["identity"],
        )

        result = reconstructor.reconstruct(scored)

        # Should contain key + value
        assert "user_name" in result or "小明" in result
        # L4 is always vivid
        assert "……" not in result or result.startswith("……")  # minimal hedge


# ============================================================
# Test Dorothy × 5 states
# ============================================================


class TestDorothyReconstruction:
    """Test Dorothy reconstruction across all 5 states."""

    def test_dorothy_vivid_with_mood_particle(
        self, l2_memory_vivid, dorothy_soul_spec, user_id
    ):
        """Dorothy vivid must have 语气词 at end."""
        # Create Dorothy version
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="宝宝养了一只叫老铁的黑猫，怕雷。",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
            emotional_peak={"valence": 0.6, "arousal": 0.7},
            emotional_end={"valence": 0.5, "arousal": 0.5},
            emotional_significance=0.7,
            importance_score=0.8,
            initial_importance=0.8,
            decay_immunity=0.0,
            state="vivid",
            recall_count=0,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # CRITICAL: Must end with 语气词
        assert any(
            result.endswith(p) for p in ["呀", "哦", "嘛", "啦", "呢", "~"]
        ), f"Dorothy must end with 语气词, got: {result}"

        # Should NOT have ellipsis (Dorothy forbids it)
        assert "……" not in result, f"Dorothy forbids ellipsis, got: {result}"

    def test_dorothy_fading_with_onomatopoeia(
        self, l2_memory_fading, dorothy_soul_spec, user_id
    ):
        """CRITICAL: Dorothy fading must have 拟声词 (诶嘿嘿, 呜哇, 嘿嘿)."""
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="宝宝的猫老铁",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(days=7),
            episode_end_at=datetime.now(timezone.utc) - timedelta(days=7),
            emotional_peak={"valence": 0.4, "arousal": 0.5},
            emotional_end={"valence": 0.3, "arousal": 0.4},
            emotional_significance=0.5,
            importance_score=0.5,
            initial_importance=0.7,
            decay_immunity=0.0,
            state="fading",
            recall_count=1,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=7),
            updated_at=datetime.now(timezone.utc) - timedelta(days=7),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.6},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # CRITICAL: Must have 拟声词
        assert any(
            ono in result for ono in ["诶嘿嘿", "呜哇", "嘿嘿"]
        ), f"Dorothy fading must have 拟声词, got: {result}"

        # Must end with 语气词
        assert any(result.endswith(p) for p in ["呀", "哦", "嘛", "啦", "呢", "~"])

        # NO ellipsis
        assert "……" not in result

    def test_dorothy_faint_state(self, l2_memory_faint, dorothy_soul_spec, user_id):
        """Dorothy faint state."""
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="宝宝的猫",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(days=30),
            episode_end_at=datetime.now(timezone.utc) - timedelta(days=30),
            emotional_peak={"valence": 0.3, "arousal": 0.4},
            emotional_end={"valence": 0.2, "arousal": 0.3},
            emotional_significance=0.4,
            importance_score=0.3,
            initial_importance=0.6,
            decay_immunity=0.0,
            state="faint",
            recall_count=0,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            updated_at=datetime.now(timezone.utc) - timedelta(days=30),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.4},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should have hedge (桃桃忘了, 好像)
        # Must end with 语气词
        assert any(result.endswith(p) for p in ["呀", "哦", "嘛", "啦", "呢", "~"])
        # NO ellipsis
        assert "……" not in result

    def test_dorothy_dormant_state(self, l2_memory_dormant, dorothy_soul_spec, user_id):
        """Dorothy dormant state."""
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="宝宝的猫怕雷",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(days=60),
            episode_end_at=datetime.now(timezone.utc) - timedelta(days=60),
            emotional_peak={"valence": 0.2, "arousal": 0.3},
            emotional_end={"valence": 0.1, "arousal": 0.2},
            emotional_significance=0.3,
            importance_score=0.15,
            initial_importance=0.5,
            decay_immunity=0.0,
            state="dormant",
            recall_count=0,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
            updated_at=datetime.now(timezone.utc) - timedelta(days=60),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.3},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should have emergence (诶？啊！我想起来了！)
        assert any(marker in result for marker in ["诶", "啊", "想起来了"])
        # Must end with 语气词 or ！
        assert result.endswith(("呀", "哦", "嘛", "啦", "呢", "~", "！"))

    def test_dorothy_archived_state(
        self, l2_memory_archived, dorothy_soul_spec, user_id
    ):
        """Dorothy archived state."""
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="宝宝养猫",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(days=90),
            episode_end_at=datetime.now(timezone.utc) - timedelta(days=90),
            emotional_peak={"valence": 0.1, "arousal": 0.2},
            emotional_end={"valence": 0.0, "arousal": 0.1},
            emotional_significance=0.2,
            importance_score=0.05,
            initial_importance=0.4,
            decay_immunity=0.0,
            state="archived",
            recall_count=0,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=90),
            updated_at=datetime.now(timezone.utc) - timedelta(days=90),
            archived_at=datetime.now(timezone.utc) - timedelta(days=10),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.2},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should have disorientation (呜哇, 诶嘿嘿, 想起来了)
        # Must end with appropriate marker
        assert len(result) > 0


# ============================================================
# Test Anti-pattern violations
# ============================================================


class TestAntiPatternChecks:
    """Test anti-pattern post-check enforcement."""

    def test_rin_hard_never_violation_raises(self, l2_memory_vivid, rin_soul_spec):
        """Rin hard_never violation should raise."""
        # Inject banned word into content
        l2_memory_vivid.episode_summary = "宝贝，你的猫很可爱。"

        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_vivid,
            memory_id=l2_memory_vivid.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        with pytest.raises(ValueError, match="宝贝"):
            reconstructor.reconstruct(scored)

    def test_rin_forbidden_pattern_violation_raises(
        self, l2_memory_vivid, rin_soul_spec
    ):
        """Rin forbidden_pattern (波浪号) violation should raise."""
        # Inject banned pattern
        l2_memory_vivid.episode_summary = "你的猫很可爱~"

        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_vivid,
            memory_id=l2_memory_vivid.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        with pytest.raises(ValueError, match="波浪号"):
            reconstructor.reconstruct(scored)

    def test_dorothy_ellipsis_forbidden(
        self, l2_memory_vivid, dorothy_soul_spec, user_id
    ):
        """Dorothy hard_never includes ……, should not appear in output."""
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="宝宝的猫很可爱",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
            emotional_peak={"valence": 0.6, "arousal": 0.7},
            emotional_end={"valence": 0.5, "arousal": 0.5},
            emotional_significance=0.7,
            importance_score=0.8,
            initial_importance=0.8,
            decay_immunity=0.0,
            state="vivid",
            recall_count=0,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Dorothy MUST NOT have ellipsis
        assert "……" not in result, f"Dorothy forbids ellipsis, got: {result}"


# ============================================================
# Test voice_dna transforms
# ============================================================


class TestVoiceTransforms:
    """Test voice_dna transform application."""

    def test_rin_avoid_we_transform(self, l2_memory_vivid, rin_soul_spec):
        """Rin vd-NEW-C: 我们 → 你和我."""
        l2_memory_vivid.episode_summary = "我们一起养猫。"

        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_vivid,
            memory_id=l2_memory_vivid.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should transform 我们 → 你和我
        assert "你和我" in result
        assert "我们" not in result

    def test_dorothy_third_person_transform(
        self, l2_memory_vivid, dorothy_soul_spec, user_id
    ):
        """Dorothy vd-DOROTHY-001: 我 → 桃桃."""
        mem = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="dorothy",
            episode_summary="我记得宝宝的猫",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
            emotional_peak={"valence": 0.6, "arousal": 0.7},
            emotional_end={"valence": 0.5, "arousal": 0.5},
            emotional_significance=0.7,
            importance_score=0.8,
            initial_importance=0.8,
            decay_immunity=0.0,
            state="vivid",
            recall_count=0,
            reinforcement_history=[],
            linked_episodes=[],
            linked_facts=[],
            reconstruction_hints={},
            do_not_recall=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )

        reconstructor = Reconstructor("dorothy", dorothy_soul_spec)
        scored = ScoredMemory(
            memory=mem,
            memory_id=mem.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        result = reconstructor.reconstruct(scored)

        # Should transform 我 → 桃桃
        assert "桃桃" in result
        assert "我记得" not in result or "桃桃记得" in result


# ============================================================
# Test cognitive_style clamping
# ============================================================


class TestCognitiveStyleClamp:
    """Test sentence length clamping."""

    def test_length_clamp(self, l2_memory_vivid, rin_soul_spec):
        """Long content should be clamped to max_length."""
        # Very long summary
        l2_memory_vivid.episode_summary = "用户养了一只叫老铁的黑猫，怕雷，喜欢吃鱼，每天晚上睡在窗台上，白天在阳台晒太阳，有时候跑到楼下花园里抓老鼠，非常活泼可爱。"

        reconstructor = Reconstructor("rin", rin_soul_spec)
        scored = ScoredMemory(
            memory=l2_memory_vivid,
            memory_id=l2_memory_vivid.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.8},
            retrieved_by=["vector"],
        )

        activation_state = {
            "current_cognitive_style": {
                "sentence_length": {"max": 30},
                "verbosity": "low",
            }
        }

        result = reconstructor.reconstruct(scored, activation_state)

        # Should be clamped to ~30 chars
        assert len(result) <= 35  # Allow small buffer


# ============================================================
# Test batch reconstruction
# ============================================================


class TestBatchReconstruction:
    """Test batch reconstruction."""

    def test_reconstruct_batch(
        self,
        l2_memory_vivid,
        l2_memory_fading,
        l2_memory_faint,
        rin_soul_spec,
    ):
        """Batch reconstruct multiple memories."""
        reconstructor = Reconstructor("rin", rin_soul_spec)

        memories = [
            ScoredMemory(
                memory=l2_memory_vivid,
                memory_id=l2_memory_vivid.id,
                memory_type="L2",
                score_breakdown={"semantic": 0.8},
                retrieved_by=["vector"],
            ),
            ScoredMemory(
                memory=l2_memory_fading,
                memory_id=l2_memory_fading.id,
                memory_type="L2",
                score_breakdown={"semantic": 0.6},
                retrieved_by=["vector"],
            ),
            ScoredMemory(
                memory=l2_memory_faint,
                memory_id=l2_memory_faint.id,
                memory_type="L2",
                score_breakdown={"semantic": 0.4},
                retrieved_by=["vector"],
            ),
        ]

        results = reconstructor.reconstruct_batch(memories)

        assert len(results) == 3
        # All should be non-empty
        assert all(len(r) > 0 for r in results)
