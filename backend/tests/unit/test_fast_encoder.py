"""
Unit tests for Fast Heuristic Encoder (SS02 §3.4).

Tests:
- Identity signal detection (name, birthday, age, occupation, pet, location)
- Sentiment analysis (positive/negative/neutral)
- Keyword fact pattern extraction
- Performance: avg latency < 30ms over 1000 calls

Author: 心屿团队
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from heart.ss02_memory.encoder.fast import FastEncoder
from heart.ss02_memory.service import Turn


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def encoder():
    """Fast Encoder instance."""
    return FastEncoder()


@pytest.fixture
def user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def character_id():
    """Test character ID."""
    return "rin"


def make_turn(content: str, user_id, character_id) -> Turn:
    """Helper to create a Turn."""
    return Turn(
        turn_index=1,
        role="user",
        content=content,
        user_id=user_id,
        character_id=character_id,
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================
# Identity Signal Detection Tests
# ============================================================


class TestIdentitySignals:
    """Tests for identity signal extraction."""

    def test_extract_name(self, encoder, user_id, character_id):
        """Should extract name from '我叫X' pattern."""
        turn = make_turn("你好，我叫李明", user_id, character_id)
        result = encoder.encode(turn)

        assert len(result.candidate_identity_signals) == 1
        signal = result.candidate_identity_signals[0]
        assert signal.type == "name"
        assert signal.value == "李明"
        assert "我叫" in signal.raw_text

    def test_extract_birthday(self, encoder, user_id, character_id):
        """Should extract birthday from '我生日X' pattern."""
        turn = make_turn("我的生日是3月14日", user_id, character_id)
        result = encoder.encode(turn)

        birthday_signals = [s for s in result.candidate_identity_signals if s.type == "birthday"]
        assert len(birthday_signals) == 1
        assert "3月14日" in birthday_signals[0].value

    def test_extract_age(self, encoder, user_id, character_id):
        """Should extract age from 'X岁' pattern."""
        turn = make_turn("我今年25岁了", user_id, character_id)
        result = encoder.encode(turn)

        age_signals = [s for s in result.candidate_identity_signals if s.type == "age"]
        assert len(age_signals) == 1
        assert age_signals[0].value == "25"

    def test_extract_occupation(self, encoder, user_id, character_id):
        """Should extract occupation from '我是X' pattern."""
        turn = make_turn("我是一名程序员", user_id, character_id)
        result = encoder.encode(turn)

        occupation_signals = [s for s in result.candidate_identity_signals if s.type == "occupation"]
        assert len(occupation_signals) == 1
        assert "程序员" in occupation_signals[0].value

    def test_extract_pet(self, encoder, user_id, character_id):
        """Should extract pet from '我养X' pattern."""
        turn = make_turn("我养了一只黑猫", user_id, character_id)
        result = encoder.encode(turn)

        pet_signals = [s for s in result.candidate_identity_signals if s.type == "pet"]
        assert len(pet_signals) == 1
        assert "黑猫" in pet_signals[0].value

    def test_extract_location(self, encoder, user_id, character_id):
        """Should extract location from '我在X' pattern."""
        turn = make_turn("我住在北京市", user_id, character_id)
        result = encoder.encode(turn)

        location_signals = [s for s in result.candidate_identity_signals if s.type == "location"]
        assert len(location_signals) == 1
        assert "北京市" in location_signals[0].value

    def test_multiple_signals_in_one_turn(self, encoder, user_id, character_id):
        """Should extract multiple signals from one turn."""
        turn = make_turn("我叫王芳，今年28岁，是老师，养了一只狗", user_id, character_id)
        result = encoder.encode(turn)

        # Should detect: name, age, occupation, pet
        assert len(result.candidate_identity_signals) >= 4

        types = {s.type for s in result.candidate_identity_signals}
        assert "name" in types
        assert "age" in types
        assert "occupation" in types
        assert "pet" in types


# ============================================================
# Sentiment Analysis Tests
# ============================================================


class TestSentiment:
    """Tests for sentiment analysis."""

    def test_positive_sentiment(self, encoder, user_id, character_id):
        """Should detect positive sentiment."""
        turn = make_turn("今天真开心，太好了，很棒！", user_id, character_id)
        result = encoder.encode(turn)

        assert result.sentiment > 0.0
        assert result.sentiment <= 1.0

    def test_negative_sentiment(self, encoder, user_id, character_id):
        """Should detect negative sentiment."""
        turn = make_turn("今天很难过，太糟糕了，很烦", user_id, character_id)
        result = encoder.encode(turn)

        assert result.sentiment < 0.0
        assert result.sentiment >= -1.0

    def test_neutral_sentiment(self, encoder, user_id, character_id):
        """Should return neutral for no sentiment words."""
        turn = make_turn("我去了图书馆", user_id, character_id)
        result = encoder.encode(turn)

        assert result.sentiment == 0.0

    def test_mixed_sentiment(self, encoder, user_id, character_id):
        """Should handle mixed sentiment."""
        turn = make_turn("虽然很累，但是很开心", user_id, character_id)
        result = encoder.encode(turn)

        # Should be slightly positive (开心 > 累)
        assert -1.0 <= result.sentiment <= 1.0


# ============================================================
# Keyword Fact Pattern Tests
# ============================================================


class TestKeywordExtraction:
    """Tests for keyword fact pattern extraction."""

    def test_extract_possession(self, encoder, user_id, character_id):
        """Should extract from '我有X' pattern."""
        turn = make_turn("我有一台MacBook", user_id, character_id)
        result = encoder.encode(turn)

        assert len(result.detected_keywords) > 0
        assert any("MacBook" in kw for kw in result.detected_keywords)

    def test_extract_like(self, encoder, user_id, character_id):
        """Should extract from '我喜欢X' pattern."""
        turn = make_turn("我喜欢看电影", user_id, character_id)
        result = encoder.encode(turn)

        assert len(result.detected_keywords) > 0
        assert any("看电影" in kw for kw in result.detected_keywords)

    def test_extract_work(self, encoder, user_id, character_id):
        """Should extract from '我工作X' pattern."""
        turn = make_turn("我的工作是做设计", user_id, character_id)
        result = encoder.encode(turn)

        assert len(result.detected_keywords) > 0
        assert any("做设计" in kw for kw in result.detected_keywords)


# ============================================================
# Integration Test: 10 Diverse Sentences
# ============================================================


class TestDiverseSentences:
    """Integration test with 10 diverse real-world sentences."""

    @pytest.mark.parametrize(
        "sentence,expected_signals,expected_sentiment_range",
        [
            # 1. Name + positive sentiment
            ("你好，我叫张伟，很高兴认识你", ["name"], (0.0, 1.0)),
            # 2. Birthday disclosure
            ("我的生日是12月25日", ["birthday"], (-0.1, 0.1)),  # neutral
            # 3. Age + occupation
            ("我今年30岁，是一名医生", ["age", "occupation"], (-0.1, 0.1)),
            # 4. Pet + positive emotion
            ("我养了一只可爱的猫咪，超级喜欢它", ["pet"], (0.3, 1.0)),
            # 5. Location + work
            ("我住在上海，在一家公司工作", ["location"], (-0.1, 0.1)),
            # 6. Negative emotion
            ("今天工作太累了，很烦躁", [], (-1.0, -0.2)),
            # 7. Mixed signals
            ("我是程序员，虽然压力大但是很喜欢编程", ["occupation"], (-0.2, 1.0)),
            # 8. Multiple identity signals
            ("我叫李娜，25岁，住在北京市", ["name", "age", "location"], (-0.1, 0.1)),
            # 9. Fact patterns
            ("我有一台iPhone，喜欢拍照", [], (0.0, 1.0)),
            # 10. Complex birthday format
            ("我生于1995年3月14日", ["birthday"], (-0.1, 0.1)),
        ],
    )
    def test_diverse_sentence(
        self,
        encoder,
        user_id,
        character_id,
        sentence,
        expected_signals,
        expected_sentiment_range,
    ):
        """Test encoding of diverse real-world sentences."""
        turn = make_turn(sentence, user_id, character_id)
        result = encoder.encode(turn)

        # Check expected signal types
        detected_types = {s.type for s in result.candidate_identity_signals}
        for expected_type in expected_signals:
            assert expected_type in detected_types, f"Expected {expected_type} in {sentence}"

        # Check sentiment range
        min_sentiment, max_sentiment = expected_sentiment_range
        assert (
            min_sentiment <= result.sentiment <= max_sentiment
        ), f"Sentiment {result.sentiment} not in [{min_sentiment}, {max_sentiment}] for: {sentence}"


# ============================================================
# Performance Test
# ============================================================


class TestPerformance:
    """Performance tests for Fast Encoder."""

    def test_latency_under_30ms(self, encoder, user_id, character_id):
        """Average latency should be < 30ms over 1000 calls.

        Spec: §10.5 fast_encode P95 < 50ms
        Our target: avg < 30ms
        """
        test_sentences = [
            "我叫李明，今年25岁",
            "我的生日是3月14日",
            "我是一名程序员",
            "我养了一只猫",
            "我住在北京市",
            "今天很开心",
            "工作很累",
            "我有一台MacBook",
            "我喜欢看电影",
            "很不错的一天",
        ]

        iterations = 1000
        start = time.perf_counter()

        for i in range(iterations):
            sentence = test_sentences[i % len(test_sentences)]
            turn = make_turn(sentence, user_id, character_id)
            encoder.encode(turn)

        end = time.perf_counter()

        total_ms = (end - start) * 1000
        avg_ms = total_ms / iterations

        print(f"\nPerformance: {iterations} calls in {total_ms:.2f}ms (avg: {avg_ms:.2f}ms/call)")

        # Assert avg < 30ms
        assert avg_ms < 30.0, f"Average latency {avg_ms:.2f}ms exceeds 30ms target"

    def test_p95_latency_under_50ms(self, encoder, user_id, character_id):
        """P95 latency should be < 50ms (spec requirement).

        Spec: §10.5 fast_encode P95 < 50ms
        """
        test_sentences = [
            "我叫李明，今年25岁，是程序员，住在北京，养了一只猫咪",  # Long sentence
            "你好",  # Short sentence
            "我的生日是1995年3月14日，很高兴认识你",  # Medium
        ]

        iterations = 1000
        latencies = []

        for i in range(iterations):
            sentence = test_sentences[i % len(test_sentences)]
            turn = make_turn(sentence, user_id, character_id)

            start = time.perf_counter()
            encoder.encode(turn)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)  # ms

        # Calculate P95
        latencies.sort()
        p95_index = int(iterations * 0.95)
        p95_latency = latencies[p95_index]

        print(f"\nP95 latency: {p95_latency:.2f}ms")

        # Assert P95 < 50ms
        assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f}ms exceeds 50ms spec"
