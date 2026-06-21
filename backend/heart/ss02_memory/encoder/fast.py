"""
Fast Heuristic Encoder — SS02 §3.4 阶段 1  (DEPRECATED — see hints/regex_hints.py)

.. deprecated::
    Identity-signal extraction has been demoted to a hints provider.
    ``candidate_identity_signals`` is always an empty list.
    L4 writes now flow through the slow-path Promoter (INV-M-11/15).

    For regex hints use ``heart.ss02_memory.hints.RegexHintsProvider``.

Real-time encoding (< 50ms) without LLM:
- Sentiment analysis (lexicon-based, valence [-1, 1])
- Keyword detection via RegexHintsProvider (as hints, not L3 writes)

Updates L1 Working Memory with FastSignals.

Performance target: P95 < 50ms (§10.5)

Author: 心屿团队
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import structlog
import yaml

from heart.ss02_memory.hints.regex_hints import Hint, RegexHintsProvider
from heart.ss02_memory.service import FastSignals, IdentitySignal, Turn

logger = structlog.get_logger()


def _load_lexicon_sentiment(lexicon_path: Optional[str] = None) -> dict:
    """Load lexicon for sentiment words only (positive/negative)."""
    if lexicon_path is None:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        lexicon_path = project_root / "config" / "encoder_lexicon.yaml"
    with open(lexicon_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class FastEncoder:
    """Fast Heuristic Encoder (< 50ms, no LLM).

    Detects:
    - Sentiment: valence [-1, 1] from lexicon
    - Keywords: via RegexHintsProvider (keyword-type hints)

    Thread-safe (no mutable shared state after init).
    """

    def __init__(self, lexicon: Optional[dict] = None):
        """Initialize Fast Encoder.

        Args:
            lexicon: Pre-loaded lexicon dict (optional, loads from default path if None)
        """
        lexicon = lexicon or _load_lexicon_sentiment()

        self._positive_words = set(lexicon.get("positive_words", []))
        self._negative_words = set(lexicon.get("negative_words", []))

        self._hints_provider = RegexHintsProvider(lexicon=lexicon)

        logger.info(
            "fast_encoder_initialized",
            positive_words=len(self._positive_words),
            negative_words=len(self._negative_words),
        )

    def encode(self, turn: Turn) -> FastSignals:
        """Encode turn into FastSignals (< 50ms).

        Args:
            turn: Conversation turn to encode

        Returns:
            FastSignals with detected keywords, sentiment, and
            **empty** candidate_identity_signals (deprecated — see
            RegexHintsProvider for regex-based hints).

        Spec: §3.4 阶段 1, §10.5 performance target P95 < 50ms
        """
        text = turn.content

        # 1. Scan for regex hints (identity + keyword facts)
        hints = self._hints_provider.scan(text)

        # 2. Populate keywords from keyword-type hints
        keywords = [h.raw_phrase for h in hints if h.suspected_attribute.startswith("keyword:")]

        # 3. Compute sentiment (lexicon-based)
        sentiment = self._compute_sentiment(text)

        # Store last hints so encode_fast() can retrieve them for enqueue
        self._last_hints = hints

        return FastSignals(
            detected_keywords=keywords,
            sentiment=sentiment,
            candidate_identity_signals=[],  # DEPRECATED — always empty
        )

    @property
    def last_hints(self) -> list[Hint]:
        """Return the hints from the most recent encode() call."""
        return getattr(self, "_last_hints", [])

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
        words = self._simple_tokenize(text)

        positive_count = sum(1 for w in words if w in self._positive_words)
        negative_count = sum(1 for w in words if w in self._negative_words)

        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            return 0.0

        valence = (positive_count - negative_count) / total_sentiment_words
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
        tokens: list[str] = []
        tokens.extend(text)

        for length in [2, 3, 4]:
            for i in range(len(text) - length + 1):
                tokens.append(text[i : i + length])

        return tokens
