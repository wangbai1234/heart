"""
Regex Hints Provider — lightweight heuristic scanner for the LLM Extractor.

Extracts candidate identity and fact signals from turn text using pre-compiled
regex patterns.  Does NOT write to any memory tier — only provides auxiliary
signals (hints) for the slow-path Extractor → Resolver → Writer pipeline.

Author: 心屿团队
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog
import yaml

logger = structlog.get_logger()


# ============================================================
# Hint dataclass
# ============================================================


@dataclass(frozen=True)
class Hint:
    """A regex-detected hint for the LLM Extractor.

    Attributes:
        raw_phrase: The matched substring.
        suspected_attribute: What this hint might be about
            (e.g. "name", "birthday", "keyword:我有", "keyword:我喜欢").
        span: Character offsets (start, end) in the source text.
    """

    raw_phrase: str
    suspected_attribute: str
    span: tuple[int, int]


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
        project_root = Path(__file__).parent.parent.parent.parent.parent
        lexicon_path = project_root / "config" / "encoder_lexicon.yaml"

    with open(lexicon_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# Regex Hints Provider
# ============================================================


class RegexHintsProvider:
    """Scans turn text with pre-compiled regex and returns Hint objects.

    Covers:
      - Identity hints: name, birthday, age, occupation, pet, location
        (patterns sourced from config/encoder_lexicon.yaml § identity_patterns).
      - Keyword fact hints: 我有/养/喜欢/工作/住在/在…工作 etc.

    This provider is stateless and thread-safe after construction.
    It does NOT trigger any memory writes.
    """

    # ── Keyword fact patterns (hard-coded, not in lexicon) ──────
    _KEYWORD_FACT_PATTERNS: list[tuple[str, str]] = [
        ("keyword:我有", r"我有(.{1,20})"),
        ("keyword:我养", r"我养(?:了)?(.{1,20})"),
        ("keyword:我喜欢", r"我喜欢(.{1,20})"),
        ("keyword:我工作", r"我(?:的)?工作(?:是)?(.{1,20})"),
        ("keyword:我住在", r"我住(?:在)?(.{1,20})"),
        ("keyword:我在", r"我在(.{1,20})(?:工作|生活|学习)"),
    ]

    def __init__(self, lexicon: Optional[dict] = None):
        """Initialise the provider.

        Args:
            lexicon: Pre-loaded lexicon dict.  If None, loads from default path.
        """
        lexicon = lexicon or load_lexicon()

        # Compile identity patterns from lexicon
        identity_config = lexicon.get("identity_patterns", {})
        self._identity_patterns: dict[str, re.Pattern] = {}
        for signal_type, pattern_str in identity_config.items():
            self._identity_patterns[signal_type] = re.compile(pattern_str)

        # Compile keyword fact patterns
        self._fact_patterns: list[tuple[str, re.Pattern]] = []
        for attr, pat in self._KEYWORD_FACT_PATTERNS:
            self._fact_patterns.append((attr, re.compile(pat)))

        logger.info(
            "regex_hints_provider_initialized",
            identity_pattern_count=len(self._identity_patterns),
            fact_pattern_count=len(self._fact_patterns),
        )

    def scan(self, turn_text: str) -> list[Hint]:
        """Scan turn text and return a list of regex-guessed hints.

        Args:
            turn_text: The user message text to scan.

        Returns:
            List of Hint objects (may be empty).
        """
        hints: list[Hint] = []

        # Identity hints (from lexicon patterns)
        for signal_type, pattern in self._identity_patterns.items():
            for match in pattern.finditer(turn_text):
                value = match.group(1) if match.groups() else match.group(0)
                hints.append(
                    Hint(
                        raw_phrase=value.strip(),
                        suspected_attribute=signal_type,
                        span=(match.start(), match.end()),
                    )
                )

        # Keyword fact hints
        for attr, pattern in self._fact_patterns:
            for match in pattern.finditer(turn_text):
                keyword = match.group(1).strip()
                if keyword:
                    hints.append(
                        Hint(
                            raw_phrase=keyword,
                            suspected_attribute=attr,
                            span=(match.start(), match.end()),
                        )
                    )

        return hints
