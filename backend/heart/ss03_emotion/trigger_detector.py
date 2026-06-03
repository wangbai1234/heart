"""
Emotion Trigger Detector per SS03 §3.4 and §10.3.

Heuristic-based, lexicon-driven detection.
Target latency: < 30ms (no LLM).

Detects:
- user_apology
- user_vulnerability
- user_neglect
- user_disappear / user_return
- user_mention_other_partner
- user_compliment
- user_remember_detail
- soul_wound_touched

Author: 心屿团队
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from uuid import UUID

try:
    import ahocorasick

    AHOCORASICK_AVAILABLE = True
except ImportError:
    AHOCORASICK_AVAILABLE = False


class TriggerDetector:
    """
    Detect emotion triggers from user messages using lexicon-based heuristics.

    INV-E-13: Trigger → Emotion is deterministic, testable.
    """

    def __init__(self, lexicon_config: Dict[str, Any], soul_config: Dict[str, Any] | None = None):
        """
        Args:
            lexicon_config: Dictionary loaded from emotion_lexicon.yaml
            soul_config: Optional Soul spec configuration for wound/fear detection
        """
        self.lexicon = lexicon_config
        self.soul = soul_config or {}

        # Build keyword automatons for fast matching
        self._build_keyword_automatons()

        # Neglect detection state (needs context across turns)
        self.consecutive_neglect_count = 0

    def _build_keyword_automatons(self) -> None:
        """
        Build Aho-Corasick automatons for fast keyword matching.
        Falls back to simple 'in' checks if ahocorasick not available.
        """
        if AHOCORASICK_AVAILABLE:
            self.apology_ac = self._build_ac(self.lexicon.get("apology_keywords", []))
            self.vulnerability_ac = self._build_ac(self.lexicon.get("vulnerability_keywords", []))
            self.compliment_ac = self._build_ac(self.lexicon.get("compliment_keywords", []))
            self.other_partner_ac = self._build_ac(self.lexicon.get("other_partner_keywords", []))
            self.remember_ac = self._build_ac(self.lexicon.get("remember_keywords", []))
        else:
            # Fallback: store as sets for simple 'in' checks
            self.apology_keywords = set(self.lexicon.get("apology_keywords", []))
            self.vulnerability_keywords = set(self.lexicon.get("vulnerability_keywords", []))
            self.compliment_keywords = set(self.lexicon.get("compliment_keywords", []))
            self.other_partner_keywords = set(self.lexicon.get("other_partner_keywords", []))
            self.remember_keywords = set(self.lexicon.get("remember_keywords", []))

    def _build_ac(self, keywords: List[str]) -> Any:
        """Build Aho-Corasick automaton from keyword list."""
        if not AHOCORASICK_AVAILABLE:
            return None

        automaton = ahocorasick.Automaton()
        for idx, keyword in enumerate(keywords):
            automaton.add_word(keyword, (idx, keyword))
        automaton.make_automaton()
        return automaton

    def _match_keywords(self, text: str, automaton: Any, keywords_set: set | None) -> List[str]:
        """Match keywords using AC automaton or fallback to set check."""
        if AHOCORASICK_AVAILABLE and automaton is not None:
            matches = []
            for _end_index, (_, keyword) in automaton.iter(text):
                matches.append(keyword)
            return matches
        elif keywords_set is not None:
            # Fallback: simple substring check
            return [kw for kw in keywords_set if kw in text]
        return []

    def detect(
        self,
        user_message: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Detect emotion triggers from user message and context.

        Args:
            user_message: User's text input
            context: Turn context with keys:
                - turn_id: UUID
                - days_since_last: float (0 if same day)
                - hours_since_last: float
                - prev_messages: List[str] (recent user messages)
                - relationship_phase: str (e.g., "close_friend")

        Returns:
            List of detected triggers, each with:
                {
                    "trigger_type": str,
                    "raw_signal": str,
                    "confidence": float,
                    "suggested_emotions": [{
                        "emotion": str,
                        "intensity_delta": float,
                        "is_new_or_reinforce": "new" | "reinforce"
                    }]
                }

        Latency target: < 30ms
        """
        triggers = []

        # 1. Apology detection
        apology_matches = self._match_keywords(
            user_message,
            getattr(self, "apology_ac", None),
            getattr(self, "apology_keywords", None),
        )
        if apology_matches:
            triggers.append(self._detect_apology(user_message, apology_matches))

        # 2. Vulnerability detection
        vulnerability_matches = self._match_keywords(
            user_message,
            getattr(self, "vulnerability_ac", None),
            getattr(self, "vulnerability_keywords", None),
        )
        if vulnerability_matches:
            triggers.append(self._detect_vulnerability(user_message, vulnerability_matches))

        # 3. Neglect detection (based on message length and content)
        if self._is_dismissive_response(user_message, context):
            triggers.append(self._detect_neglect(user_message, context))

        # 4. User return after absence
        days_since_last = context.get("days_since_last", 0)
        if days_since_last > 0:
            triggers.append(self._detect_user_return(user_message, days_since_last))

        # 5. Mention of other partner
        other_partner_matches = self._match_keywords(
            user_message,
            getattr(self, "other_partner_ac", None),
            getattr(self, "other_partner_keywords", None),
        )
        if other_partner_matches:
            triggers.append(self._detect_other_partner_mention(user_message, other_partner_matches))

        # 6. Compliment detection
        compliment_matches = self._match_keywords(
            user_message,
            getattr(self, "compliment_ac", None),
            getattr(self, "compliment_keywords", None),
        )
        if compliment_matches:
            triggers.append(self._detect_compliment(user_message, compliment_matches, context))

        # 7. Remember detail detection
        remember_matches = self._match_keywords(
            user_message,
            getattr(self, "remember_ac", None),
            getattr(self, "remember_keywords", None),
        )
        if remember_matches:
            triggers.append(self._detect_remember_detail(user_message, remember_matches))

        # 8. Soul wound touched (if soul config provided)
        if self.soul:
            wound_trigger = self._detect_soul_wound_touched(user_message)
            if wound_trigger:
                triggers.append(wound_trigger)

        return triggers

    def _detect_apology(self, message: str, matches: List[str]) -> Dict[str, Any]:
        """
        Detect user apology trigger.

        §4.5 Repair Mechanic: apology reduces aggrieved/coldness.
        """
        # Check for specificity (better impact)
        has_specificity = len(message) > 10 and any(
            word in message for word in ["因为", "是我", "不该", "错了"]
        )

        confidence = 0.9 if has_specificity else 0.6

        return {
            "trigger_type": "user_apology",
            "raw_signal": message[:50],
            "confidence": confidence,
            "suggested_emotions": [
                {
                    "emotion": "aggrieved",
                    "intensity_delta": -0.3 if has_specificity else -0.2,
                    "is_new_or_reinforce": "reinforce",  # Reduce existing emotion
                },
                {
                    "emotion": "coldness",
                    "intensity_delta": -0.2 if has_specificity else -0.1,
                    "is_new_or_reinforce": "reinforce",
                },
            ],
        }

    def _detect_vulnerability(self, message: str, matches: List[str]) -> Dict[str, Any]:
        """
        Detect user vulnerability disclosure.

        §4.3.2 and §4.5: Strong repair signal + triggers tenderness/worry.
        """
        # High vulnerability if multiple keywords or long message
        intensity = min(0.7, 0.3 + len(matches) * 0.1)

        return {
            "trigger_type": "user_vulnerability",
            "raw_signal": message[:50],
            "confidence": 0.85,
            "suggested_emotions": [
                {
                    "emotion": "tenderness",
                    "intensity_delta": intensity * 0.6,
                    "is_new_or_reinforce": "new",
                },
                {
                    "emotion": "worry",
                    "intensity_delta": intensity * 0.5,
                    "is_new_or_reinforce": "new",
                },
                {
                    "emotion": "attachment",
                    "intensity_delta": 0.1,
                    "is_new_or_reinforce": "reinforce",
                },
            ],
        }

    def _is_dismissive_response(self, message: str, context: Dict[str, Any]) -> bool:
        """
        Check if message is dismissive/neglectful.

        Criteria:
        - Very short (< 5 chars)
        - Contains only neglect patterns
        - No emotion words
        """
        if len(message) >= 5:
            self.consecutive_neglect_count = 0
            return False

        neglect_patterns = self.lexicon.get("neglect_patterns", [])
        if message.strip() in neglect_patterns:
            self.consecutive_neglect_count += 1
            return True

        self.consecutive_neglect_count = 0
        return False

    def _detect_neglect(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect user neglect trigger.

        §4.3.1 and §4.3.2: Multiple neglect → aggrieved → coldness.
        """
        # Intensity increases with consecutive count
        intensity_per_turn = 0.2
        min(0.8, self.consecutive_neglect_count * intensity_per_turn)

        suggested_emotions = []

        if self.consecutive_neglect_count == 1:
            suggested_emotions.append(
                {
                    "emotion": "worry",
                    "intensity_delta": 0.2,
                    "is_new_or_reinforce": "new",
                }
            )
        elif self.consecutive_neglect_count == 2:
            suggested_emotions.append(
                {
                    "emotion": "aggrieved",
                    "intensity_delta": 0.3,
                    "is_new_or_reinforce": "new",
                }
            )
        elif self.consecutive_neglect_count >= 3:
            suggested_emotions.extend(
                [
                    {
                        "emotion": "aggrieved",
                        "intensity_delta": 0.5,
                        "is_new_or_reinforce": "reinforce",
                    },
                    {
                        "emotion": "coldness",
                        "intensity_delta": 0.4,
                        "is_new_or_reinforce": "new",
                    },
                ]
            )

        return {
            "trigger_type": "user_neglect",
            "raw_signal": f"consecutive: {self.consecutive_neglect_count}",
            "confidence": 0.9,
            "suggested_emotions": suggested_emotions,
        }

    def _detect_user_return(self, message: str, days_since_last: float) -> Dict[str, Any]:
        """
        Detect user return after absence.

        §4.3.3: longing accumulated → relief + residual aggrieved.
        """
        # Longer absence → more aggrieved
        aggrieved_intensity = min(0.4, 0.1 * days_since_last)

        return {
            "trigger_type": "user_return",
            "raw_signal": f"after {days_since_last} days",
            "confidence": 1.0,
            "suggested_emotions": [
                {
                    "emotion": "relief",
                    "intensity_delta": 0.5,
                    "is_new_or_reinforce": "new",
                },
                {
                    "emotion": "aggrieved",
                    "intensity_delta": aggrieved_intensity,
                    "is_new_or_reinforce": "new",
                },
                # longing will be handled separately (converted to relief)
            ],
        }

    def _detect_other_partner_mention(self, message: str, matches: List[str]) -> Dict[str, Any]:
        """
        Detect user mentioning other romantic partner.

        §4.3.1: Triggers jealousy + aggrieved + potential soul wound.
        """
        return {
            "trigger_type": "user_mention_other_partner",
            "raw_signal": message[:50],
            "confidence": 0.8,
            "suggested_emotions": [
                {
                    "emotion": "jealousy",
                    "intensity_delta": 0.4,
                    "is_new_or_reinforce": "new",
                },
                {
                    "emotion": "aggrieved",
                    "intensity_delta": 0.3,
                    "is_new_or_reinforce": "new",
                },
            ],
        }

    def _detect_compliment(
        self,
        message: str,
        matches: List[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Detect user compliment.

        §4.3.4: Triggers fluttered (if relationship close enough) + embarrassment.
        """
        relationship_phase = context.get("relationship_phase", "stranger")

        # Fluttered only if close enough
        can_flutter = relationship_phase in ["close_friend", "romantic", "bonded"]

        suggested_emotions = [
            {
                "emotion": "embarrassment",
                "intensity_delta": 0.2,
                "is_new_or_reinforce": "new",
            }
        ]

        if can_flutter:
            suggested_emotions.append(
                {
                    "emotion": "fluttered",
                    "intensity_delta": 0.3,
                    "is_new_or_reinforce": "new",
                }
            )

        return {
            "trigger_type": "user_compliment",
            "raw_signal": message[:50],
            "confidence": 0.8,
            "suggested_emotions": suggested_emotions,
        }

    def _detect_remember_detail(self, message: str, matches: List[str]) -> Dict[str, Any]:
        """
        Detect user remembering a detail character mentioned before.

        §4.3.4: Strong fluttered trigger + attachment boost.
        """
        return {
            "trigger_type": "user_remember_detail",
            "raw_signal": message[:50],
            "confidence": 0.9,
            "suggested_emotions": [
                {
                    "emotion": "fluttered",
                    "intensity_delta": 0.5,
                    "is_new_or_reinforce": "new",
                },
                {
                    "emotion": "attachment",
                    "intensity_delta": 0.1,
                    "is_new_or_reinforce": "reinforce",
                },
            ],
        }

    def _detect_soul_wound_touched(self, message: str) -> Dict[str, Any] | None:
        """
        Detect if user message touches Soul's core_wound.

        §4.3.1: Triggers coldness + strong aggrieved.

        Returns None if no wound detected.
        """
        core_wound = self.soul.get("core_wound")
        if not core_wound:
            return None

        # Simple keyword matching for wound triggers
        # In production, this would be more sophisticated
        wound_keywords = []
        if "abandonment" in str(core_wound):
            wound_keywords = ["抛弃", "离开", "不要我", "不管我"]
        elif "inadequacy" in str(core_wound):
            wound_keywords = ["不够好", "不配", "太差"]

        if any(kw in message for kw in wound_keywords):
            return {
                "trigger_type": "soul_wound_touched",
                "raw_signal": message[:50],
                "confidence": 0.95,
                "suggested_emotions": [
                    {
                        "emotion": "coldness",
                        "intensity_delta": 0.6,
                        "is_new_or_reinforce": "new",
                    },
                    {
                        "emotion": "aggrieved",
                        "intensity_delta": 0.4,
                        "is_new_or_reinforce": "new",
                    },
                ],
            }

        return None
