"""
LLM Encoder Worker - SS02 §3.4 阶段 2

Async worker that processes memory encoding events:
- Consumes memory_encoding_events with status='llm_pending'
- Calls cheap LLM (DeepSeek V3) with MEMORY_EXTRACTION_PROMPT
- Parses JSON output strictly (附录 A schema)
- Writes facts to L3 FactNode table
- Handles malformed JSON with retry (max 2)
- Idempotent via event_id deduplication

Performance target: 100 events/sec, LLM timeout 10s

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings
from heart.infra.llm_providers import get_model_router
from heart.prompts.memory_extraction import MEMORY_EXTRACTION_PROMPT
from heart.ss02_memory.models import FactNode, MemoryEncodingEvent
from heart.ss02_memory.predicate_vocab import build_embedding_text, normalize_predicate

logger = structlog.get_logger()


async def _embed_fact_text(text: str) -> Optional[list[float]]:
    """Embed an L3 fact's literal text, best-effort.

    Returns None when no embedding service is configured (no EMBEDDING_API_KEY)
    or on any failure, leaving semantic_vector NULL (recall then falls back to
    recency/identity). Populating this is REQUIRED for the fact to be reachable
    by the VectorRetriever, which filters `semantic_vector IS NOT NULL` and is the
    only working L3 retrieval path in the hot loop.
    """
    try:
        from heart.api.wiring import get_embedding_service

        embedder = get_embedding_service()
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("embedding_service_unavailable", error=str(e))
        return None
    if embedder is None:
        return None
    try:
        return await embedder.embed_query(text)
    except Exception as e:
        logger.warning("l3_embedding_failed", error=str(e))
        return None


# ============================================================
# Configuration
# ============================================================

MAX_RETRIES = 2
LLM_TIMEOUT_SECONDS = 10
BATCH_SIZE = 10  # Process 10 events per batch
POLL_INTERVAL_SECONDS = 5  # Poll every 5 seconds when idle


# ============================================================
# JSON Schema Validation
# ============================================================


def validate_extraction_output(data: dict) -> tuple[bool, Optional[str]]:  # noqa: C901
    """Validate LLM extraction output matches schema.

    Args:
        data: Parsed JSON from LLM

    Returns:
        (is_valid, error_message)
    """
    # Check required top-level fields
    required_fields = [
        "facts",
        "emotion_peak",
        "importance_estimate",
        "contains_sacred",
        "contains_promise",
        "contains_first_event",
    ]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate facts array
    if not isinstance(data["facts"], list):
        return False, "'facts' must be a list"

    for i, fact in enumerate(data["facts"]):
        required_fact_fields = [
            "predicate",
            "subject",
            "object",
            "source_text",
            "confidence",
            "emotional_charge",
            "emotional_label",
            "sacred_signal",
        ]

        for field in required_fact_fields:
            if field not in fact:
                return False, f"Fact {i}: missing field '{field}'"

        # Validate confidence
        if not isinstance(fact["confidence"], (int, float)):
            return False, f"Fact {i}: confidence must be a number"

        if not 0 <= fact["confidence"] <= 1:
            return False, f"Fact {i}: confidence must be in [0, 1]"

        # Validate emotional_charge
        if not isinstance(fact["emotional_charge"], (int, float)):
            return False, f"Fact {i}: emotional_charge must be a number"

    # Validate emotion_peak
    emotion_peak = data["emotion_peak"]
    if not isinstance(emotion_peak, dict):
        return False, "'emotion_peak' must be a dict"

    for field in ["valence", "arousal", "label"]:
        if field not in emotion_peak:
            return False, f"emotion_peak: missing field '{field}'"

    # Validate importance_estimate
    if not isinstance(data["importance_estimate"], (int, float)):
        return False, "'importance_estimate' must be a number"

    if not 0 <= data["importance_estimate"] <= 1:
        return False, "'importance_estimate' must be in [0, 1]"

    # Validate boolean flags
    for field in ["contains_sacred", "contains_promise", "contains_first_event"]:
        if not isinstance(data[field], bool):
            return False, f"'{field}' must be a boolean"

    return True, None


# ============================================================
# Prompt Builder
# ============================================================


def build_extraction_prompt(
    user_text: str,
    assistant_text: str,
    character_id: str,
    recent_context: Optional[dict] = None,
) -> str:
    """Build MEMORY_EXTRACTION_PROMPT with variables substituted.

    Args:
        user_text: User's message
        assistant_text: Assistant's response
        character_id: Character ID (e.g., "rin")
        recent_context: Recent conversation turns (optional)

    Returns:
        Formatted prompt string
    """
    # Format recent context
    if recent_context and "turns" in recent_context:
        context_lines = []
        for turn in recent_context["turns"]:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            context_lines.append(f"{role}: {content}")
        recent_context_str = "\n".join(context_lines)
    else:
        recent_context_str = "(无)"

    # Substitute variables
    prompt = MEMORY_EXTRACTION_PROMPT.format(
        recent_context=recent_context_str,
        user_text=user_text,
        assistant_text=assistant_text,
        character_id=character_id,
    )

    return prompt


# ============================================================
# Fact Writer
# ============================================================


async def write_facts_to_l3(
    session: AsyncSession,
    event: MemoryEncodingEvent,
    extraction: dict,
) -> list[UUID]:
    """Write extracted facts to L3 FactNode table.

    Args:
        session: Database session
        event: Source encoding event
        extraction: Validated LLM extraction output

    Returns:
        List of created fact IDs
    """
    created_fact_ids = []

    for fact in extraction["facts"]:
        # Skip low-confidence facts (spec: confidence < 0.7 不输出)
        if fact["confidence"] < 0.7:
            logger.info(
                "skipped_low_confidence_fact",
                event_id=str(event.event_id),
                predicate=fact["predicate"],
                confidence=fact["confidence"],
            )
            continue

        # Canonicalise the predicate before dedup so synonym predicates
        # (e.g. concerned_about / worries_about) converge to the same row.
        canonical_pred = normalize_predicate(fact["predicate"])

        existing_stmt = select(FactNode).where(
            FactNode.user_id == event.user_id,
            FactNode.character_id == event.character_id,
            FactNode.predicate == canonical_pred,
            FactNode.subject == fact["subject"],
            ~FactNode.do_not_recall,
        )

        result = await session.execute(existing_stmt)
        existing_fact = result.scalar_one_or_none()

        if existing_fact:
            # Fact exists - reinforce it (阶段 3 logic, simplified here)
            existing_fact.confirmation_count += 1
            existing_fact.confidence = max(existing_fact.confidence, fact["confidence"])
            existing_fact.last_confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Backfill / refresh embedding with aligned Chinese text so the
            # fact is reachable by Chinese recall queries.
            if existing_fact.semantic_vector is None:
                embed_text = build_embedding_text(
                    existing_fact.subject, existing_fact.predicate, existing_fact.object
                )
                existing_fact.semantic_vector = await _embed_fact_text(embed_text)

            # Add this turn to source_turn_ids
            if event.source_turn_id not in existing_fact.source_turn_ids:
                existing_fact.source_turn_ids.append(event.source_turn_id)

            logger.info(
                "reinforced_existing_fact",
                event_id=str(event.event_id),
                fact_id=str(existing_fact.id),
                predicate=canonical_pred,
                confirmation_count=existing_fact.confirmation_count,
            )

            created_fact_ids.append(existing_fact.id)
        else:
            # Create new fact — store canonical predicate in the DB.
            # literal_text uses the canonical predicate (display is unaffected).
            literal_text = f"{fact['subject']} {canonical_pred} {fact['object']}"
            # Embed Chinese-aligned text so the VectorRetriever can match
            # Chinese recall queries against this fact.
            semantic_vector = await _embed_fact_text(
                build_embedding_text(fact["subject"], canonical_pred, fact["object"])
            )
            fact_node = FactNode(
                id=uuid4(),
                user_id=event.user_id,
                character_id=event.character_id,
                predicate=canonical_pred,
                subject=fact["subject"],
                object=fact["object"],
                literal_text=literal_text,
                raw_evidence=fact["source_text"],
                source_turn_ids=[event.source_turn_id],
                confidence=fact["confidence"],
                emotional_charge=fact["emotional_charge"],
                emotional_label=fact.get("emotional_label"),
                importance=extraction["importance_estimate"],
                is_identity_level=fact.get("sacred_signal", False) or extraction["contains_sacred"],
                state="active",
                semantic_vector=semantic_vector,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

            session.add(fact_node)

            logger.info(
                "created_new_fact",
                event_id=str(event.event_id),
                fact_id=str(fact_node.id),
                predicate=fact["predicate"],
                confidence=fact["confidence"],
            )

            created_fact_ids.append(fact_node.id)

    return created_fact_ids


# ============================================================
# LLM Encoder Worker
# ============================================================


class MemoryEncoderWorker:
    """LLM Encoder Worker (阶段 2).

    Processes encoding events asynchronously with LLM fact extraction.
    """

    def __init__(self, db_session_factory):
        """Initialize worker.

        Args:
            db_session_factory: Async session factory for database access
        """
        self.db_session_factory = db_session_factory
        self._should_stop = False

        logger.info(
            "memory_encoder_worker_initialized",
            max_retries=MAX_RETRIES,
            llm_timeout=LLM_TIMEOUT_SECONDS,
            batch_size=BATCH_SIZE,
        )

    async def start(self):
        """Start worker loop.

        Continuously polls for pending events and processes them.
        """
        logger.info("memory_encoder_worker_started")

        while not self._should_stop:
            try:
                # Fetch pending events
                async with self.db_session_factory() as session:
                    events = await self._fetch_pending_events(session)

                if not events:
                    # No pending events - sleep and retry
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
                    continue

                # Group same-(user,character) events so each group needs one LLM call.
                groups = self._group_events(events)
                logger.info("processing_batch", count=len(events), groups=len(groups))

                for group in groups:
                    try:
                        await self._process_event_group(group)
                    except Exception as e:
                        logger.error(
                            "event_group_processing_failed",
                            user_id=str(group[0].user_id),
                            character_id=group[0].character_id,
                            count=len(group),
                            error=str(e),
                        )

            except Exception as e:
                logger.error(
                    "worker_loop_error",
                    error=str(e),
                )
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

        logger.info("memory_encoder_worker_stopped")

    async def stop(self):
        """Stop worker gracefully."""
        logger.info("memory_encoder_worker_stopping")
        self._should_stop = True

    async def _fetch_pending_events(self, session: AsyncSession) -> list[MemoryEncodingEvent]:
        """Fetch pending encoding events.

        Args:
            session: Database session

        Returns:
            List of pending events (status='llm_pending')
        """
        stmt = (
            select(MemoryEncodingEvent)
            .where(MemoryEncodingEvent.status == "llm_pending")
            .order_by(MemoryEncodingEvent.created_at)
            .limit(BATCH_SIZE)
        )

        result = await session.execute(stmt)
        events = result.scalars().all()

        return list(events)

    def _group_events(self, events: list[MemoryEncodingEvent]) -> list[list[MemoryEncodingEvent]]:
        """Group pending events by (user_id, character_id), preserving first-seen order.

        Each group is capped at memory_extractor_batch_turns so a large backlog does not
        build one enormous extraction prompt; the overflow is picked up next cycle.
        """
        cap = max(1, settings.memory_extractor_batch_turns)
        order: list[tuple] = []
        buckets: dict[tuple, list[MemoryEncodingEvent]] = {}
        for e in events:
            key = (e.user_id, e.character_id)
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(e)
        return [buckets[k][:cap] for k in order]

    async def _process_event_group(self, events: list[MemoryEncodingEvent]):
        """Process a group of same-(user,character) events.

        A single-event group (or batching disabled) uses the per-event path unchanged.
        Multi-event groups combine the turns into ONE extraction LLM call and mark every
        event in the group done with the shared result.
        """
        if len(events) == 1 or not settings.memory_batch_extraction_enabled:
            for event in events:
                await self._process_event(event)
            return

        event_ids = [e.event_id for e in events]
        async with self.db_session_factory() as session:
            stmt = select(MemoryEncodingEvent).where(MemoryEncodingEvent.event_id.in_(event_ids))
            result = await session.execute(stmt)
            current = [e for e in result.scalars().all() if e.status != "llm_done"]
            if not current:
                return
            # Keep chronological order so the representative event is the latest turn.
            current.sort(key=lambda e: e.created_at)

            started = datetime.now(timezone.utc).replace(tzinfo=None)
            for e in current:
                e.llm_started_at = started
            await session.commit()

            try:
                extraction = await self._call_llm_extraction_batch(current)
                representative = current[-1]
                fact_ids = await write_facts_to_l3(session, representative, extraction)

                completed = datetime.now(timezone.utc).replace(tzinfo=None)
                for e in current:
                    e.status = "llm_done"
                    e.llm_extraction = extraction
                    e.llm_completed_at = completed
                await session.commit()

                logger.info(
                    "event_group_processed",
                    user_id=str(representative.user_id),
                    character_id=representative.character_id,
                    events=len(current),
                    facts_created=len(fact_ids),
                )
            except Exception as e:
                for ev in current:
                    ev.retry_count += 1
                    if ev.retry_count >= MAX_RETRIES:
                        ev.status = "failed"
                        ev.failed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        ev.failure_reason = str(e)
                    # else: stays llm_pending for retry next cycle
                await session.commit()
                logger.error("event_group_failed", events=len(current), error=str(e))

    async def _process_event(self, event: MemoryEncodingEvent):
        """Process a single encoding event.

        Args:
            event: Encoding event to process
        """
        event_id = str(event.event_id)

        logger.info(
            "processing_event",
            event_id=event_id,
            user_id=str(event.user_id),
            character_id=event.character_id,
            retry_count=event.retry_count,
        )

        async with self.db_session_factory() as session:
            # Check if already processed (idempotency)
            # Reload event to get latest state
            stmt = select(MemoryEncodingEvent).where(MemoryEncodingEvent.event_id == event.event_id)
            result = await session.execute(stmt)
            current_event = result.scalar_one_or_none()

            if current_event is None:
                logger.warning("event_not_found", event_id=event_id)
                return

            if current_event.status == "llm_done":
                logger.info("event_already_processed", event_id=event_id)
                return

            # Mark as started
            current_event.llm_started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()

            try:
                # Call LLM
                extraction = await self._call_llm_extraction(current_event)

                # Write facts to L3
                fact_ids = await write_facts_to_l3(session, current_event, extraction)

                # Update event as successful
                current_event.status = "llm_done"
                current_event.llm_extraction = extraction
                current_event.llm_completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

                await session.commit()

                logger.info(
                    "event_processed_successfully",
                    event_id=event_id,
                    facts_created=len(fact_ids),
                )

            except Exception as e:
                # Handle failure with retry
                current_event.retry_count += 1

                if current_event.retry_count >= MAX_RETRIES:
                    current_event.status = "failed"
                    current_event.failed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    current_event.failure_reason = str(e)

                    logger.error(
                        "event_failed_max_retries",
                        event_id=event_id,
                        error=str(e),
                        retry_count=current_event.retry_count,
                    )
                else:
                    # Keep as llm_pending for retry
                    logger.warning(
                        "event_failed_will_retry",
                        event_id=event_id,
                        error=str(e),
                        retry_count=current_event.retry_count,
                    )

                await session.commit()
                raise

    async def _call_llm_extraction(self, event: MemoryEncodingEvent) -> dict:
        """Call LLM to extract facts from event.

        Args:
            event: Encoding event

        Returns:
            Validated extraction output (dict)

        Raises:
            ValueError: If JSON parsing or validation fails
            TimeoutError: If LLM call times out
        """
        # Build prompt
        prompt = build_extraction_prompt(
            user_text=event.source_user_text or "",
            assistant_text=event.source_assistant_text or "",
            character_id=event.character_id,
            recent_context=event.recent_context,
        )
        return await self._run_extraction(prompt)

    async def _call_llm_extraction_batch(self, events: list[MemoryEncodingEvent]) -> dict:
        """Extract facts from a group of turns in ONE LLM call.

        The user/assistant texts of each turn are concatenated; facts are turn-agnostic,
        so the extraction schema is unchanged. recent_context comes from the earliest turn.
        """
        user_text = "\n".join(
            (e.source_user_text or "").strip() for e in events if e.source_user_text
        )
        assistant_text = "\n".join(
            (e.source_assistant_text or "").strip() for e in events if e.source_assistant_text
        )
        prompt = build_extraction_prompt(
            user_text=user_text,
            assistant_text=assistant_text,
            character_id=events[0].character_id,
            recent_context=events[0].recent_context,
        )
        return await self._run_extraction(prompt)

    async def _run_extraction(self, prompt: str) -> dict:
        """Send an extraction prompt to the cheap model and validate the JSON result."""
        router = await get_model_router()

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            response = await asyncio.wait_for(
                router.call_cheap(
                    messages=messages,
                    temperature=0.0,  # Deterministic for fact extraction
                    max_tokens=2000,
                    json_mode=True,
                    agent_name="memory_encoder",
                ),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM call timed out after {LLM_TIMEOUT_SECONDS}s") from None

        # Parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}") from e

        # Validate schema
        is_valid, error_msg = validate_extraction_output(data)
        if not is_valid:
            raise ValueError(f"Invalid extraction schema: {error_msg}")

        return data
