"""
Anti-Pattern Filter — SS05 Persona Composition Runtime §3.8 (§10.7)

Synchronous post-generation filter that scans LLM output against
per-character Soul.anti_patterns.  Uses Aho-Corasick automaton for
literal hard_never patterns and compiled regex for forbidden_patterns.

Per runtime_specs/05_persona_composition_runtime.md:
- §3.3 Step 9: Full Anti-Pattern Filter (sync, < 20ms)
- §10.7: AntiPatternFilter class with AC + regex dual-strategy
- PC-4:  Hard anti-patterns must be intercepted (sync filter)
- INV-PC-3: No released response may match soul.anti_patterns.hard_never
- C-PC-4: Anti-pattern filter intercept rate ≤ 0.5%
- Performance: p95 ≤ 10ms, p99 ≤ 25ms (§10.9)

Design contract:
- Deterministic — no LLM calls
- Aho-Corasick for literal substring matching (O(n + m) where n = text len, m = matches)
- Compiled regex for pattern-level checks
- Returns FilterResult with passed boolean and detailed violation list

Author: 心屿团队
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import ahocorasick

    AHOCORASICK_AVAILABLE = True
except ImportError:
    AHOCORASICK_AVAILABLE = False


# ============================================================
# Data types
# ============================================================


@dataclass
class FilterViolation:
    """A single anti-pattern violation found in text.

    Mirrors the violation reporting structure implied by §5.6 AntiPatternConfig
    and the filter output contract in §10.7.
    """

    pattern: str
    """The matched literal substring or regex pattern description."""

    violation_type: str
    """Category: 'hard_never' | 'forbidden_pattern'."""

    match_excerpt: str = ""
    """The specific text that triggered the match (contextual)."""


@dataclass
class FilterResult:
    """Output of AntiPatternFilter.filter().

    Per §10.7 return contract:
      - action="pass"    → passed=True, violations=[]
      - action="reroll"  → passed=False, violations=[...], severity="hard"
      - action="warn"    → passed=True (w/ soft_never), violations=[...], severity="soft"
    """

    passed: bool
    """True if no hard_never or forbidden_pattern violations found."""

    violations: List[FilterViolation] = field(default_factory=list)
    """List of all detected violations."""

    severity: str = ""
    """'hard' when reroll is required, 'soft' for warn-only, '' for clean."""

    def __bool__(self) -> bool:
        return self.passed


# ============================================================
# AntiPatternFilter
# ============================================================


class AntiPatternFilter:
    """Synchronous full-message anti-pattern filter.

    Builds Aho-Corasick automaton from hard_never literal patterns
    and compiles regex for forbidden_patterns at init time.

    Usage:
        >>> filter = AntiPatternFilter(soul)
        >>> result = filter.filter("some llm output")
        >>> if result.passed:
        ...     release_to_user()
        ... else:
        ...     trigger_reroll(result)
    """

    def __init__(self, soul: Dict[str, Any]):
        """
        Args:
            soul: Soul spec dict (or dict with 'anti_patterns' key).
                  Anti-patterns are extracted from soul['anti_patterns'].
                  Supports both raw YAML-loaded dict and Pydantic model dump.
        """
        anti = soul.get("anti_patterns", {}) if isinstance(soul, dict) else {}

        # ── hard_never literals → AC automaton ──
        self._hard_never_literals: List[str] = list(anti.get("hard_never", []) or [])
        self._ac: Any = None
        if AHOCORASICK_AVAILABLE and self._hard_never_literals:
            self._ac = ahocorasick.Automaton()
            for idx, literal in enumerate(self._hard_never_literals):
                self._ac.add_word(literal, (idx, literal))
            self._ac.make_automaton()

        # ── forbidden_patterns → compiled regex ──
        self._forbidden_patterns: List[Dict[str, Any]] = []
        raw_forbidden = anti.get("forbidden_patterns", []) or []
        for spec in raw_forbidden:
            if isinstance(spec, dict):
                try:
                    compiled = re.compile(spec["regex"])
                except re.error:
                    continue
                self._forbidden_patterns.append({
                    "description": spec.get("description", spec["regex"]),
                    "regex": spec.get("regex", ""),
                    "compiled": compiled,
                    "exception": spec.get("exception"),
                })
            elif isinstance(spec, str):
                try:
                    compiled = re.compile(spec)
                except re.error:
                    continue
                self._forbidden_patterns.append({
                    "description": spec,
                    "regex": spec,
                    "compiled": compiled,
                    "exception": None,
                })

        # ── soft_never (stage-gated, reserved for future use) ──
        self._soft_never: List[str] = list(anti.get("soft_never", []) or [])

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def filter(self, text: str) -> FilterResult:
        """Run full hard-never + forbidden-pattern scan on text.

        Args:
            text: The LLM-generated response text to scan.

        Returns:
            FilterResult with passed=True if clean, or passed=False
            with detailed violations if any hard_never or forbidden_pattern
            is found.
        """
        violations: List[FilterViolation] = []

        # ── Pass 1: Aho-Corasick on hard_never literals ──
        if self._ac is not None:
            for end_idx, (_, literal) in self._ac.iter(text):
                # Extract a short context window around the match
                start = max(0, end_idx - len(literal) - 10)
                end = min(len(text), end_idx + 10)
                excerpt = text[start:end]
                violations.append(
                    FilterViolation(
                        pattern=literal,
                        violation_type="hard_never",
                        match_excerpt=excerpt,
                    )
                )
        elif self._hard_never_literals:
            # Fallback: O(n*m) substring scan
            for literal in self._hard_never_literals:
                idx = text.find(literal)
                if idx != -1:
                    start = max(0, idx - 10)
                    end = min(len(text), idx + len(literal) + 10)
                    violations.append(
                        FilterViolation(
                            pattern=literal,
                            violation_type="hard_never",
                            match_excerpt=text[start:end],
                        )
                    )

        # ── Pass 2: Compiled regex on forbidden_patterns ──
        for fp in self._forbidden_patterns:
            match = fp["compiled"].search(text)
            if match:
                violations.append(
                    FilterViolation(
                        pattern=fp["description"],
                        violation_type="forbidden_pattern",
                        match_excerpt=match.group(),
                    )
                )

        if violations:
            return FilterResult(
                passed=False,
                violations=violations,
                severity="hard",
            )

        return FilterResult(passed=True, violations=[], severity="")

    # ----------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------

    @property
    def pattern_count(self) -> int:
        """Total number of patterns loaded (hard_never + forbidden)."""
        return len(self._hard_never_literals) + len(self._forbidden_patterns)

    @property
    def hard_never_count(self) -> int:
        """Number of hard_never literal patterns."""
        return len(self._hard_never_literals)

    @property
    def forbidden_pattern_count(self) -> int:
        """Number of compiled forbidden regex patterns."""
        return len(self._forbidden_patterns)

    @property
    def automaton(self):
        """The compiled Aho-Corasick automaton for hard_never literals.

        Returns None if pyahocorasick is not installed or if the hard_never
        list is empty.  The automaton is shared with the StreamingPreFilter
        so both filters use the exact same pattern set (§3 streaming design).
        """
        return self._ac

    @property
    def hard_never_literals(self) -> list:
        """The raw hard_never literal strings (for introspection / config checks)."""
        return list(self._hard_never_literals)

    @property
    def max_pattern_length(self) -> int:
        """Length of the longest hard_never literal, in characters.

        Used by StreamingPreFilter to size scan_window and hold_window.
        Returns 0 when the hard_never list is empty.
        """
        if not self._hard_never_literals:
            return 0
        return max(len(p) for p in self._hard_never_literals)

    # ----------------------------------------------------------
    # Startup safety check
    # ----------------------------------------------------------

    def check_literal_lengths(self, max_allowed: int = 40) -> list[str]:
        """Warn about hard_never literals exceeding the recommended cap.

        Per streaming design §2 recommendation: cap individual hard_never
        literals at 40 chars so first-byte-to-user latency stays bounded.
        Literals longer than this should be reclassified as forbidden_patterns
        (regex).

        Args:
            max_allowed: Maximum recommended literal length in characters.

        Returns:
            List of warning messages (empty if all literals are within bounds).
        """
        warnings = []
        for literal in self._hard_never_literals:
            if len(literal) > max_allowed:
                warnings.append(
                    f"hard_never literal '{literal[:40]}...' is {len(literal)} chars; "
                    f"recommend ≤ {max_allowed}. Consider reclassifying as forbidden_pattern."
                )
        return warnings


# ============================================================
# Convenience function
# ============================================================


def filter_text(text: str, soul: Dict[str, Any]) -> FilterResult:
    """Convenience one-shot: build filter from soul spec and scan text.

    Args:
        text: LLM-generated response text.
        soul: Soul spec dict containing anti_patterns.

    Returns:
        FilterResult with passed + violations.
    """
    f = AntiPatternFilter(soul)
    return f.filter(text)
