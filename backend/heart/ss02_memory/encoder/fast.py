"""
Fast Heuristic Encoder - SS02 §3.4 阶段 1

Real-time encoding (< 50ms) without LLM:
- Identity signal extraction (name, birthday, age, occupation, pet, location)
- Sentiment analysis (lexicon-based, valence [-1, 1])
- Keyword fact pattern detection (我有/养/喜欢/工作 X)

Updates L1 Working Memory with FastSignals.

Performance target: P95 < 50ms (§10.5)

Author: 心屿团队
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import structlog
import yaml

from heart.ss02_memory.service import FastSignals, IdentitySignal, Turn

logger = structlog.get_logger()


# ============================================================
# Lexicon Loader
# ============================================================


def load_lexicon(lexicon_path: Optional[str] = None) -> dict:
    """Load encoder lexicon from YAML.

    Args:
        lexicon_path: Path to lexicon YAML (defaults to config/encoder_lexicon.yaml)

    Returns:
        Lexicon dict with positive_words, negative_words, identity_patterns
    """
    if lexicon_path is None:
        # Default path relative to project root
        # __file__ = .../heart/backend/heart/ss02_memory/encoder/fast.py
        # → parent x5 = .../heart
        project_root = Path(__file__).parent.parent.parent.parent.parent
        lexicon_path = project_root / "config" / "encoder_lexicon.yaml"

    with open(lexicon_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# Fast Heuristic Encoder
# ============================================================


class FastEncoder:
    """Fast Heuristic Encoder (< 50ms, no LLM).

    Detects:
    - Identity signals: name, birthday, age, occupation, pet, location
    - Sentiment: valence [-1, 1] from lexicon
    - Keyword fact patterns: 我有/养/喜欢/工作 X

    Thread-safe (no mutable shared state after init).
    """

    def __init__(self, lexicon: Optional[dict] = None):
        """Initialize Fast Encoder.

        Args:
            lexicon: Pre-loaded lexicon dict (optional, loads from default path if None)
        """
        # Load lexicon
        self._lexicon = lexicon or load_lexicon()

        # Build word sets for fast lookup
        self._positive_words = set(self._lexicon.get("positive_words", []))
        self._negative_words = set(self._lexicon.get("negative_words", []))

        # Pre-compile all regex patterns
        self._identity_patterns = self._compile_identity_patterns(
            self._lexicon.get("identity_patterns", {})
        )

        # Pre-compile keyword fact patterns
        self._fact_patterns = self._compile_fact_patterns()

        logger.info(
            "fast_encoder_initialized",
            positive_words=len(self._positive_words),
            negative_words=len(self._negative_words),
            identity_patterns=len(self._identity_patterns),
        )

    def encode(self, turn: Turn) -> FastSignals:
        """Encode turn into FastSignals (< 50ms).

        Args:
            turn: Conversation turn to encode

        Returns:
            FastSignals with detected keywords, sentiment, identity signals

        Spec: §3.4 阶段 1, §10.5 performance target P95 < 50ms
        """
        text = turn.content

        # 1. Extract identity signals (regex)
        identity_signals = self._extract_identity_signals(text)

        # 2. Detect sentiment (lexicon-based)
        sentiment = self._compute_sentiment(text)

        # 3. Extract keywords from fact patterns
        keywords = self._extract_keywords(text)

        return FastSignals(
            detected_keywords=keywords,
            sentiment=sentiment,
            candidate_identity_signals=identity_signals,
        )

    # ─────────── Identity Signal Extraction ───────────

    def _compile_identity_patterns(self, patterns_config: dict) -> dict[str, re.Pattern]:
        """Pre-compile identity regex patterns.

        Args:
            patterns_config: Dict of {type: pattern_string}

        Returns:
            Dict of {type: compiled_regex}
        """
        compiled = {}
        for signal_type, pattern_str in patterns_config.items():
            compiled[signal_type] = re.compile(pattern_str)
        return compiled

    def _extract_identity_signals(self, text: str) -> list[IdentitySignal]:
        """Extract identity signals from text using regex.

        Detects: name, birthday, age, occupation, pet, location

        Args:
            text: Input text

        Returns:
            List of IdentitySignal
        """
        signals = []

        for signal_type, pattern in self._identity_patterns.items():
            for match in pattern.finditer(text):
                # Extract captured group (the value)
                value = match.group(1) if match.groups() else match.group(0)

                signals.append(
                    IdentitySignal(
                        type=signal_type,
                        value=value.strip(),
                        raw_text=match.group(0),
                    )
                )

        return signals

    # ─────────── Sentiment Analysis ───────────

    def _compute_sentiment(self, text: str) -> float:
        """Compute sentiment valence [-1, 1] from lexicon.

        Simple word-counting approach:
        - Count positive words vs negative words
        - Normalize by total words

        Args:
            text: Input text

        Returns:
            Valence score [-1, 1]
        """
        # Tokenize (simple, character-level for Chinese)
        # For Chinese, we use character-level to catch compound words
        # For a production system, you'd use jieba, but we want sub-50ms
        words = self._simple_tokenize(text)

        positive_count = sum(1 for w in words if w in self._positive_words)
        negative_count = sum(1 for w in words if w in self._negative_words)

        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            return 0.0

        # Valence: (positive - negative) / total
        valence = (positive_count - negative_count) / total_sentiment_words

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, valence))

    def _simple_tokenize(self, text: str) -> list[str]:
        """Simple tokenizer for Chinese text.

        Extracts all substrings of length 2-4 (to catch common Chinese words).
        Also extracts single characters.

        This is faster than jieba and sufficient for lexicon matching.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        tokens = []

        # Extract single characters
        tokens.extend(text)

        # Extract 2-4 character sequences
        for length in [2, 3, 4]:
            for i in range(len(text) - length + 1):
                tokens.append(text[i : i + length])

        return tokens

    # ─────────── Keyword Fact Patterns ───────────

    def _compile_fact_patterns(self) -> list[re.Pattern]:
        """Pre-compile keyword fact patterns.

        Patterns: 我有/养/喜欢/工作/住在 X

        Returns:
            List of compiled regex patterns
        """
        patterns = [
            re.compile(r"我有(.{1,20})"),
            re.compile(r"我养(?:了)?(.{1,20})"),
            re.compile(r"我喜欢(.{1,20})"),
            re.compile(r"我(?:的)?工作(?:是)?(.{1,20})"),
            re.compile(r"我住(?:在)?(.{1,20})"),
            re.compile(r"我在(.{1,20})(?:工作|生活|学习)"),
        ]
        return patterns

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from fact patterns.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        keywords = []

        for pattern in self._fact_patterns:
            for match in pattern.finditer(text):
                keyword = match.group(1).strip()
                if keyword:
                    keywords.append(keyword)

        return keywords
