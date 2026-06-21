"""
SS02 Memory — Regex Shadow Writer for dual-mode comparison.

When MEMORY_EXTRACTOR_MODE=dual, this module extracts facts from turn text
using the same regex patterns as RegexHintsProvider and writes them to the
shadow table ``memory_l3_facts_shadow_regex``.  The LLM path continues to
write to the main ``fact_nodes`` table.

The daily diff report (heart/scripts/extractor_diff_report.py) compares
both tables to measure recall/precision gaps.

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.extractor.types import TurnInput
from heart.ss02_memory.hints.regex_hints import RegexHintsProvider
from heart.ss02_memory.models import MemoryL3FactShadowRegex

logger = structlog.get_logger()

# Fixed confidence for regex-extracted facts (no ML model behind them).
_REGEX_CONFIDENCE = 0.5

# Map regex suspected_attribute → (predicate, subject) pairs.
# This mirrors the LLM extraction taxonomy so cross-path alignment works.
_ATTRIBUTE_TO_PREDICATE: dict[str, tuple[str, str]] = {
    "name": ("name", "self"),
    "birthday": ("birthday", "self"),
    "age": ("age", "self"),
    "occupation": ("occupation", "self"),
    "pet": ("has_pet", "self"),
    "pet_name": ("pet_name", "pet"),
    "location": ("location_residence", "self"),
    "keyword:我有": ("has_possession", "self"),
    "keyword:我养": ("has_pet", "self"),
    "keyword:我喜欢": ("likes", "self"),
    "keyword:我工作": ("occupation", "self"),
    "keyword:我住在": ("location_residence", "self"),
    "keyword:我在": ("location_work", "self"),
}


class RegexShadowWriter:
    """Extracts facts from turn text using regex and writes to shadow table.

    Stateless and thread-safe after construction.

    Usage::

        writer = RegexShadowWriter()
        await writer.write(turns, user_id, extractor_run_id, session)
    """

    def __init__(self) -> None:
        self._hints_provider = RegexHintsProvider()

    async def write(
        self,
        turns: list[TurnInput],
        user_id: UUID,
        character_id: str,
        extractor_run_id: UUID,
        session: AsyncSession,
    ) -> int:
        """Run regex extraction over turns and write facts to shadow table.

        Args:
            turns: TurnInput list from the extraction window.
            user_id: Owner user.
            character_id: Character identifier (usually "default").
            extractor_run_id: Links to the LLM extractor run that triggered this.
            session: Active async DB session.

        Returns:
            Number of facts written to the shadow table.
        """
        written = 0
        now = datetime.now(timezone.utc)

        for turn in turns:
            if turn.speaker != "user":
                continue

            hints = self._hints_provider.scan(turn.text)

            for hint in hints:
                mapped = _ATTRIBUTE_TO_PREDICATE.get(hint.suspected_attribute)
                if mapped is None:
                    continue

                predicate, subject = mapped
                value = hint.raw_phrase

                fact = MemoryL3FactShadowRegex(
                    id=uuid4(),
                    user_id=user_id,
                    character_id=character_id,
                    predicate=predicate,
                    subject=subject,
                    object=value,
                    literal_text=f"{subject}: {predicate} = {value}",
                    raw_evidence=f"regex_match: {hint.suspected_attribute}",
                    source_turn_ids=[],
                    source_turns=[turn.turn_id],
                    confidence=_REGEX_CONFIDENCE,
                    extractor_run_id=extractor_run_id,
                    matched_llm_fact_id=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(fact)
                written += 1

        if written > 0:
            await session.flush()
            logger.info(
                "regex_shadow_writer_committed",
                extractor_run_id=str(extractor_run_id),
                written=written,
            )

        return written
