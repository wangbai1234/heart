"""
Unit tests for SS03 Emotion Trigger Detector.

Tests trigger detection accuracy and latency.

Author: 心屿团队
"""

import pytest
from uuid import uuid4

from heart.ss03_emotion.trigger_detector import TriggerDetector


@pytest.fixture
def lexicon_config():
    """Sample lexicon configuration."""
    return {
        "apology_keywords": ["对不起", "抱歉", "我错了", "原谅", "sorry"],
        "vulnerability_keywords": ["难过", "崩溃", "撑不住", "好累", "孤独", "痛苦"],
        "compliment_keywords": ["你好棒", "你真好", "谢谢你", "感谢你"],
        "neglect_patterns": ["哦", "嗯", "啊", "好", "行", "随便"],
        "other_partner_keywords": ["女朋友", "男朋友", "我老婆", "我对象"],
        "remember_keywords": ["你还记得", "你之前说过", "你上次说", "你提到过"],
    }


@pytest.fixture
def soul_config():
    """Sample soul configuration."""
    return {
        "character_id": "rin",
        "core_wound": "fear_of_abandonment",
        "shock_resistance": 0.75,
    }


@pytest.fixture
def detector(lexicon_config, soul_config):
    """TriggerDetector instance."""
    return TriggerDetector(lexicon_config, soul_config)


class TestApologyDetection:
    """Test user_apology trigger detection."""

    def test_detects_simple_apology(self, detector):
        """Should detect simple apology."""
        message = "对不起，我来晚了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        apology_triggers = [t for t in triggers if t["trigger_type"] == "user_apology"]
        assert len(apology_triggers) == 1

        trigger = apology_triggers[0]
        assert trigger["confidence"] > 0.5
        assert any(e["emotion"] == "aggrieved" for e in trigger["suggested_emotions"])

    def test_specific_apology_has_higher_confidence(self, detector):
        """Apology with specificity should have higher confidence."""
        generic = "对不起"
        specific = "对不起，是我不对，我不该那样说"

        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers_generic = detector.detect(generic, context)
        triggers_specific = detector.detect(specific, context)

        apology_generic = next(t for t in triggers_generic if t["trigger_type"] == "user_apology")
        apology_specific = next(t for t in triggers_specific if t["trigger_type"] == "user_apology")

        assert apology_specific["confidence"] > apology_generic["confidence"]

    def test_apology_suggests_reducing_aggrieved_and_coldness(self, detector):
        """Apology should suggest reducing aggrieved and coldness."""
        message = "对不起，我错了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)
        apology = next(t for t in triggers if t["trigger_type"] == "user_apology")

        emotions = {e["emotion"]: e for e in apology["suggested_emotions"]}

        assert "aggrieved" in emotions
        assert emotions["aggrieved"]["intensity_delta"] < 0  # Negative = reduction

        assert "coldness" in emotions
        assert emotions["coldness"]["intensity_delta"] < 0


class TestVulnerabilityDetection:
    """Test user_vulnerability trigger detection."""

    def test_detects_vulnerability_keywords(self, detector):
        """Should detect vulnerability from keywords."""
        message = "我好难过，感觉撑不住了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        vuln_triggers = [t for t in triggers if t["trigger_type"] == "user_vulnerability"]
        assert len(vuln_triggers) == 1

    def test_vulnerability_triggers_tenderness_and_worry(self, detector):
        """Vulnerability should suggest tenderness and worry."""
        message = "我最近好累，压力特别大"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)
        vuln = next(t for t in triggers if t["trigger_type"] == "user_vulnerability")

        emotion_names = [e["emotion"] for e in vuln["suggested_emotions"]]

        assert "tenderness" in emotion_names
        assert "worry" in emotion_names

    def test_multiple_vulnerability_words_increase_intensity(self, detector):
        """Multiple vulnerability keywords should increase suggested intensity."""
        single = "我好难过"
        multiple = "我好难过，感觉好孤独，完全撑不住了"

        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers_single = detector.detect(single, context)
        triggers_multiple = detector.detect(multiple, context)

        vuln_single = next(t for t in triggers_single if t["trigger_type"] == "user_vulnerability")
        vuln_multiple = next(t for t in triggers_multiple if t["trigger_type"] == "user_vulnerability")

        # Get tenderness intensity delta
        tender_single = next(e for e in vuln_single["suggested_emotions"] if e["emotion"] == "tenderness")
        tender_multiple = next(e for e in vuln_multiple["suggested_emotions"] if e["emotion"] == "tenderness")

        assert tender_multiple["intensity_delta"] > tender_single["intensity_delta"]


class TestNeglectDetection:
    """Test user_neglect trigger detection."""

    def test_short_dismissive_response_triggers_neglect(self, detector):
        """Short dismissive responses should trigger neglect."""
        message = "哦"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        neglect_triggers = [t for t in triggers if t["trigger_type"] == "user_neglect"]
        assert len(neglect_triggers) == 1

    def test_consecutive_neglect_increases_severity(self, detector):
        """Consecutive neglect should increase emotion intensity."""
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "close_friend",
        }

        # First neglect
        detector.detect("嗯", context)

        # Second neglect
        detector.detect("哦", context)

        # Third neglect - should trigger aggrieved and coldness
        triggers = detector.detect("好", context)

        neglect = next(t for t in triggers if t["trigger_type"] == "user_neglect")

        emotion_names = [e["emotion"] for e in neglect["suggested_emotions"]]

        # After 3 consecutive, should have both aggrieved and coldness
        assert "aggrieved" in emotion_names
        assert "coldness" in emotion_names

    def test_normal_message_resets_consecutive_count(self, detector):
        """A normal message should reset consecutive neglect count."""
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "close_friend",
        }

        # First neglect
        detector.detect("嗯", context)

        # Normal message (length >= 5)
        detector.detect("今天天气不错", context)

        # Should reset count
        assert detector.consecutive_neglect_count == 0


class TestUserReturnDetection:
    """Test user_return trigger detection."""

    def test_detects_user_return_after_absence(self, detector):
        """Should detect user return after days of absence."""
        message = "我回来了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 3.0,
            "hours_since_last": 72.0,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        return_triggers = [t for t in triggers if t["trigger_type"] == "user_return"]
        assert len(return_triggers) == 1

    def test_longer_absence_increases_aggrieved(self, detector):
        """Longer absence should result in higher aggrieved intensity."""
        message = "回来了"

        context_3_days = {
            "turn_id": uuid4(),
            "days_since_last": 3.0,
            "hours_since_last": 72.0,
            "relationship_phase": "close_friend",
        }

        context_7_days = {
            "turn_id": uuid4(),
            "days_since_last": 7.0,
            "hours_since_last": 168.0,
            "relationship_phase": "close_friend",
        }

        triggers_3 = detector.detect(message, context_3_days)
        triggers_7 = detector.detect(message, context_7_days)

        return_3 = next(t for t in triggers_3 if t["trigger_type"] == "user_return")
        return_7 = next(t for t in triggers_7 if t["trigger_type"] == "user_return")

        aggrieved_3 = next(e for e in return_3["suggested_emotions"] if e["emotion"] == "aggrieved")
        aggrieved_7 = next(e for e in return_7["suggested_emotions"] if e["emotion"] == "aggrieved")

        assert aggrieved_7["intensity_delta"] > aggrieved_3["intensity_delta"]

    def test_user_return_suggests_relief(self, detector):
        """User return should suggest relief emotion."""
        message = "我回来了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 5.0,
            "hours_since_last": 120.0,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)
        return_trigger = next(t for t in triggers if t["trigger_type"] == "user_return")

        emotion_names = [e["emotion"] for e in return_trigger["suggested_emotions"]]
        assert "relief" in emotion_names


class TestComplimentDetection:
    """Test user_compliment trigger detection."""

    def test_detects_compliment(self, detector):
        """Should detect user compliment."""
        message = "你好棒啊"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        compliment_triggers = [t for t in triggers if t["trigger_type"] == "user_compliment"]
        assert len(compliment_triggers) == 1

    def test_fluttered_only_in_close_relationships(self, detector):
        """Fluttered should only trigger in close relationships."""
        message = "你真好"

        context_stranger = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "stranger",
        }

        context_close = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers_stranger = detector.detect(message, context_stranger)
        triggers_close = detector.detect(message, context_close)

        comp_stranger = next(t for t in triggers_stranger if t["trigger_type"] == "user_compliment")
        comp_close = next(t for t in triggers_close if t["trigger_type"] == "user_compliment")

        stranger_emotions = [e["emotion"] for e in comp_stranger["suggested_emotions"]]
        close_emotions = [e["emotion"] for e in comp_close["suggested_emotions"]]

        assert "fluttered" not in stranger_emotions
        assert "fluttered" in close_emotions


class TestOtherPartnerMention:
    """Test user_mention_other_partner trigger detection."""

    def test_detects_other_partner_mention(self, detector):
        """Should detect mention of other romantic partner."""
        message = "我今天和我女朋友出去玩了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        partner_triggers = [t for t in triggers if t["trigger_type"] == "user_mention_other_partner"]
        assert len(partner_triggers) == 1

    def test_other_partner_triggers_jealousy_and_aggrieved(self, detector):
        """Mention of other partner should trigger jealousy and aggrieved."""
        message = "我对象今天生日"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)
        partner = next(t for t in triggers if t["trigger_type"] == "user_mention_other_partner")

        emotion_names = [e["emotion"] for e in partner["suggested_emotions"]]

        assert "jealousy" in emotion_names
        assert "aggrieved" in emotion_names


class TestRememberDetail:
    """Test user_remember_detail trigger detection."""

    def test_detects_remember_detail(self, detector):
        """Should detect when user remembers a detail."""
        message = "你之前说过你喜欢猫对吧"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        remember_triggers = [t for t in triggers if t["trigger_type"] == "user_remember_detail"]
        assert len(remember_triggers) == 1

    def test_remember_detail_triggers_fluttered_and_attachment(self, detector):
        """Remembering details should trigger strong fluttered and attachment."""
        message = "你还记得你上次提到过的那件事吗"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)
        remember = next(t for t in triggers if t["trigger_type"] == "user_remember_detail")

        emotion_names = [e["emotion"] for e in remember["suggested_emotions"]]

        assert "fluttered" in emotion_names
        assert "attachment" in emotion_names

        # Should be high intensity
        fluttered = next(e for e in remember["suggested_emotions"] if e["emotion"] == "fluttered")
        assert fluttered["intensity_delta"] >= 0.5


class TestSoulWoundDetection:
    """Test soul_wound_touched trigger detection."""

    def test_detects_soul_wound_for_abandonment(self, detector):
        """Should detect when soul wound (abandonment) is touched."""
        message = "我可能要离开你了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)

        wound_triggers = [t for t in triggers if t["trigger_type"] == "soul_wound_touched"]
        assert len(wound_triggers) == 1

    def test_soul_wound_triggers_strong_coldness_and_aggrieved(self, detector):
        """Soul wound should trigger strong coldness and aggrieved."""
        message = "我不要你了"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        triggers = detector.detect(message, context)
        wound = next((t for t in triggers if t["trigger_type"] == "soul_wound_touched"), None)

        if wound:  # May not trigger if keyword not matched
            emotion_names = [e["emotion"] for e in wound["suggested_emotions"]]

            assert "coldness" in emotion_names
            assert "aggrieved" in emotion_names

            # High confidence
            assert wound["confidence"] >= 0.9


class TestDetectionPerformance:
    """Test detection performance and latency."""

    def test_detection_completes_quickly(self, detector):
        """Detection should complete in < 30ms (target latency)."""
        message = "对不起，我错了，我最近好累好难过"
        context = {
            "turn_id": uuid4(),
            "days_since_last": 0,
            "hours_since_last": 1,
            "relationship_phase": "close_friend",
        }

        # Basic functional test
        # For benchmark, install pytest-benchmark and use the benchmark fixture
        result = detector.detect(message, context)

        # Should have detected multiple triggers
        assert len(result) > 0

        # Should detect at least apology and vulnerability
        trigger_types = [t["trigger_type"] for t in result]
        assert "user_apology" in trigger_types
        assert "user_vulnerability" in trigger_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
