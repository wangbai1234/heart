"""
SS02 Memory LLM Extractor — Main extractor class

All LLM calls go through heart.infra.llm.router (INV-M-11).
On structured output validation failure: retry once with error feedback.
On second failure: mark queue item failed, log structured error.
Enforces cost cap from settings (MEMORY_EXTRACTOR_COST_CAP_USD).

Author: 心屿团队
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional
from uuid import uuid4

import structlog

from heart.core.config import settings
from heart.infra.llm_providers import ModelRouter

from .cost_guard import CostCapExceeded, CostGuard
from .prompt_builder import MODEL, PROMPT_VERSION, SCHEMA_VERSION, PromptBuilder
from .types import (
    ExtractionEnvelope,
    ExtractorRunResult,
    QueueItem,
)

logger = structlog.get_logger()

# Schema JSON for tool definition
_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "emit_extraction_envelope",
        "description": "Emit the structured extraction envelope for this conversation window.",
        "parameters": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "extractor_run_id",
                "model",
                "prompt_version",
                "schema_version",
                "window",
                "candidates",
                "dropped_signals",
            ],
            "properties": {
                "extractor_run_id": {"type": "string", "format": "uuid"},
                "model": {"type": "string", "minLength": 1, "maxLength": 100},
                "prompt_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "schema_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "window": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["turn_ids", "size"],
                    "properties": {
                        "turn_ids": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0},
                            "minItems": 1,
                            "maxItems": 64,
                        },
                        "size": {"type": "integer", "ge": 1, "le": 64},
                    },
                },
                "candidates": {
                    "type": "array",
                    "maxItems": 32,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "entity_type",
                            "attribute",
                            "value",
                            "source_turns",
                            "confidence",
                            "kind",
                            "operation",
                            "reasoning",
                        ],
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "enum": [
                                    "self",
                                    "pet",
                                    "family",
                                    "friend",
                                    "colleague",
                                    "location",
                                    "possession",
                                    "preference",
                                    "event",
                                    "other",
                                ],
                            },
                            "attribute": {
                                "type": "string",
                                "enum": [
                                    "name",
                                    "nickname",
                                    "age",
                                    "color",
                                    "breed",
                                    "occupation",
                                    "relation",
                                    "location_residence",
                                    "location_origin",
                                    "hobby",
                                    "dislike",
                                    "health_condition",
                                    "birthday",
                                    "anniversary",
                                    "other",
                                ],
                            },
                            "value": {"type": "string", "minLength": 1, "maxLength": 500},
                            "entity_ref": {"type": ["string", "null"], "maxLength": 100},
                            "prior_value_id": {"type": ["string", "null"], "format": "uuid"},
                            "source_turns": {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0},
                                "minItems": 1,
                                "maxItems": 16,
                            },
                            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "kind": {
                                "type": "string",
                                "enum": [
                                    "disclosure",
                                    "rhetoric",
                                    "question",
                                    "negation",
                                    "hypothetical",
                                ],
                            },
                            "operation": {
                                "type": "string",
                                "enum": ["create", "update", "supersede", "soft_delete"],
                            },
                            "reasoning": {"type": "string", "minLength": 1, "maxLength": 200},
                        },
                    },
                },
                "dropped_signals": {
                    "type": "array",
                    "maxItems": 32,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["turn_id", "raw_phrase", "reason"],
                        "properties": {
                            "turn_id": {"type": "integer", "minimum": 0},
                            "raw_phrase": {"type": "string", "minLength": 1, "maxLength": 500},
                            "reason": {
                                "type": "string",
                                "enum": [
                                    "ambiguous_reference",
                                    "out_of_scope_entity",
                                    "out_of_scope_attribute",
                                    "low_confidence",
                                    "sarcasm_or_rhetoric",
                                    "duplicate_of_l3",
                                    "insufficient_context",
                                    "other",
                                ],
                            },
                        },
                    },
                },
            },
        },
    },
}


def _build_tool_choice() -> dict[str, Any]:
    """Build tool_choice parameter forcing emit_extraction_envelope."""
    return {"type": "function", "function": {"name": "emit_extraction_envelope"}}


class LLMExtractor:
    """LLM Memory Extractor — extracts structured facts from conversation windows.

    All LLM calls go through heart.infra.llm.router (INV-M-11).
    On structured output validation failure: retry once with error feedback.
    On second failure: mark queue item failed, log structured error.
    Enforces per-run cost cap from settings.

    Usage:
        router = await get_model_router()
        extractor = LLMExtractor(router)
        result = await extractor.run(queue_item)
    """

    def __init__(
        self,
        router: ModelRouter,
        prompt_version: str = PROMPT_VERSION,
        schema_version: str = SCHEMA_VERSION,
        cost_guard: CostGuard | None = None,
    ):
        self._router = router
        self._prompt_builder = PromptBuilder(prompt_version, schema_version)
        self._cost_guard = cost_guard or CostGuard()
        self._model = MODEL

    async def run(self, batch: list[QueueItem]) -> list[ExtractorRunResult]:
        """Process a batch of queue items through the LLM extractor.

        Args:
            batch: List of QueueItem to process.

        Returns:
            List of ExtractorRunResult, one per input item.
        """
        results = []
        for item in batch:
            result = await self._process_one(item)
            results.append(result)
        return results

    async def _process_one(self, item: QueueItem) -> ExtractorRunResult:
        """Process a single QueueItem through the LLM extractor.

        Args:
            item: QueueItem to process.

        Returns:
            ExtractorRunResult with envelope or error.
        """
        run_id = str(item.extractor_run_id)
        start_time = time.monotonic()

        # Build the prompt
        system_prompt = self._prompt_builder.build(
            window=item.window,
            l3_snapshot=item.l3_snapshot,
            hints=item.hints,
            extractor_run_id=item.extractor_run_id,
            model=item.model,
        )

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract facts from the conversation window above."},
        ]

        # Estimate cost and check cap (conservative: ~3.3k input, ~500 output)
        estimated_input_tokens = len(system_prompt) // 2  # rough chars→tokens
        estimated_output_tokens = 500
        try:
            self._cost_guard.check_before_call(
                run_id,
                estimated_input_tokens,
                estimated_output_tokens,
            )
        except CostCapExceeded as e:
            logger.warning(
                "cost_cap_exceeded_before_extraction",
                run_id=run_id,
                error=str(e),
            )
            return ExtractorRunResult(
                envelope=self._empty_envelope(item),
                failed=True,
                error=str(e),
                latency_ms=int((time.monotonic() - start_time) * 1000),
            )

        # First attempt
        try:
            envelope, input_tokens, output_tokens, cost_usd = await self._call_llm(
                messages, item, run_id
            )
        except (ValueError, json.JSONDecodeError) as e:
            # Malformed JSON from LLM — treat as parse error, retry once
            logger.warning(
                "extraction_parse_error_retrying",
                run_id=run_id,
                error=str(e),
            )
            retry_result = await self._retry_with_error_feedback(
                messages,
                item,
                run_id,
                f"JSON parse error: {e}",
                start_time,
                0,
                0,
                0.0,
            )
            if retry_result is not None:
                return retry_result
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return ExtractorRunResult(
                envelope=self._empty_envelope(item),
                failed=True,
                error=f"Parse error after retry: {e}",
                latency_ms=latency_ms,
                retry_count=1,
            )

        # Record actual cost
        try:
            self._cost_guard.record_actual(run_id, cost_usd)
        except CostCapExceeded as e:
            logger.warning(
                "cost_cap_exceeded_after_extraction",
                run_id=run_id,
                error=str(e),
            )
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return ExtractorRunResult(
                envelope=envelope,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                failed=True,
                error=str(e),
            )

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Validate envelope — retry once with error feedback on failure
        validation_error = self._validate_envelope(envelope, item)
        if validation_error is not None:
            logger.warning(
                "extraction_validation_failed_retrying",
                run_id=run_id,
                error=validation_error,
            )
            retry_result = await self._retry_with_error_feedback(
                messages,
                item,
                run_id,
                validation_error,
                start_time,
                input_tokens,
                output_tokens,
                cost_usd,
            )
            if retry_result is not None:
                return retry_result

            # Second failure — mark as failed
            logger.error(
                "extraction_validation_failed_permanently",
                run_id=run_id,
                error=validation_error,
                candidates_count=len(envelope.candidates),
            )
            return ExtractorRunResult(
                envelope=envelope,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                latency_ms=int((time.monotonic() - start_time) * 1000),
                retry_count=1,
                failed=True,
                error=f"Validation failed after retry: {validation_error}",
            )

        logger.info(
            "extraction_succeeded",
            extractor_run_id=run_id,
            candidates_count=len(envelope.candidates),
            dropped_count=len(envelope.dropped_signals),
            cost_usd=f"{cost_usd:.6f}",
            latency_ms=latency_ms,
        )

        return ExtractorRunResult(
            envelope=envelope,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        item: QueueItem,
        run_id: str,
    ) -> tuple[ExtractionEnvelope, int, int, float]:
        """Make the LLM call and parse the response.

        Returns:
            Tuple of (envelope, input_tokens, output_tokens, cost_usd).
        """
        # Build request with tool use
        from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole

        typed_messages = [
            Message(role=MessageRole(m["role"]), content=m["content"]) for m in messages
        ]

        request = LLMRequest(
            messages=typed_messages,
            model=item.model,
            temperature=0.0,
            max_tokens=1024,
            json_mode=False,
        )

        provider = self._router._registry.get_provider_for_model(item.model)
        response = await provider.call(request)

        # Extract content
        content = response.content
        input_tokens = response.usage.get("prompt_tokens", 0)
        output_tokens = response.usage.get("completion_tokens", 0)

        # Estimate cost
        cost_estimate = provider.estimate_cost(input_tokens, output_tokens, item.model)
        cost_usd = cost_estimate.total_cost_usd

        # Parse JSON from response (handle tool-call wrapper if present)
        parsed = self._parse_llm_response(content)

        # Sanitize dropped_signals.reason — map unknown enum values to "other"
        from .types import DroppedReason

        _valid_reasons = {r.value for r in DroppedReason}
        if "dropped_signals" in parsed:
            for ds in parsed["dropped_signals"]:
                if isinstance(ds, dict) and "reason" in ds:
                    if ds["reason"] not in _valid_reasons:
                        logger.warning(
                            "sanitizing_dropped_reason",
                            original=ds["reason"],
                            fallback="other",
                        )
                        ds["reason"] = "other"

        # Validate and convert to ExtractionEnvelope
        envelope = ExtractionEnvelope(**parsed)

        return envelope, input_tokens, output_tokens, cost_usd

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """Parse LLM response, extracting JSON from tool-call wrapper if needed.

        Args:
            content: Raw LLM response content.

        Returns:
            Parsed dict matching ExtractionEnvelope schema.
        """
        # Try direct JSON parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting from tool-call wrapper: ```json ... ``` or {"arguments": "..."}
        import re

        # Match ```json ... ``` blocks
        json_match = re.search(r"```json\s*\n?(.*?)\n?\s*```", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Match {"arguments": "{...}"} pattern (some providers wrap tool calls)
        args_match = re.search(r'"arguments"\s*:\s*"(\{.*?\})"', content, re.DOTALL)
        if args_match:
            # Unescape the JSON string
            args_str = args_match.group(1).replace('\\"', '"').replace("\\\\", "\\")
            return json.loads(args_str)

        raise ValueError(f"Could not extract JSON from LLM response: {content[:200]}...")

    def _validate_envelope(self, envelope: ExtractionEnvelope, item: QueueItem) -> str | None:
        """Validate envelope against business rules.

        Returns:
            Error message if validation fails, None if valid.
        """
        # Check window.turn_ids matches
        expected_turn_ids = sorted(t.turn_id for t in item.window)
        actual_turn_ids = sorted(envelope.window.turn_ids)
        if expected_turn_ids != actual_turn_ids:
            return f"Window turn_ids mismatch: expected {expected_turn_ids}, got {actual_turn_ids}"

        # Check window.size matches
        if envelope.window.size != len(item.window):
            return f"Window size mismatch: expected {len(item.window)}, got {envelope.window.size}"

        # Check metadata echo
        if str(envelope.extractor_run_id) != str(item.extractor_run_id):
            return (
                f"extractor_run_id mismatch: expected {item.extractor_run_id}, "
                f"got {envelope.extractor_run_id}"
            )

        if envelope.prompt_version != item.prompt_version:
            return (
                f"prompt_version mismatch: expected {item.prompt_version}, "
                f"got {envelope.prompt_version}"
            )

        if envelope.schema_version != item.schema_version:
            return (
                f"schema_version mismatch: expected {item.schema_version}, "
                f"got {envelope.schema_version}"
            )

        # Validate source_turns ⊆ window.turn_ids
        valid_turn_ids = set(t.turn_id for t in item.window)
        for candidate in envelope.candidates:
            for st in candidate.source_turns:
                if st not in valid_turn_ids:
                    return f"Candidate source_turn {st} not in window.turn_ids {valid_turn_ids}"

        return None

    async def _retry_with_error_feedback(
        self,
        messages: list[dict[str, str]],
        item: QueueItem,
        run_id: str,
        validation_error: str,
        start_time: float,
        prev_input_tokens: int,
        prev_output_tokens: int,
        prev_cost_usd: float,
    ) -> ExtractorRunResult | None:
        """Retry with error feedback appended to the prompt.

        Returns:
            ExtractorRunResult on success, None if retry also fails.
        """
        # Append error feedback to the user message
        error_feedback = (
            f"\n\n[SYSTEM] Previous extraction failed validation: {validation_error}. "
            f"Please fix the issues and re-extract. Pay attention to: "
            f"1) source_turns must be subset of window.turn_ids, "
            f"2) window.turn_ids and size must match the input, "
            f"3) all metadata fields must be echoed exactly."
        )
        messages_with_feedback = messages.copy()
        messages_with_feedback[-1] = {
            "role": "user",
            "content": messages[-1]["content"] + error_feedback,
        }

        try:
            envelope, input_tokens, output_tokens, cost_usd = await self._call_llm(
                messages_with_feedback, item, run_id
            )
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(
                "extraction_retry_parse_error",
                run_id=run_id,
                error=str(e),
            )
            return None

        # Record retry cost
        total_cost = prev_cost_usd + cost_usd
        try:
            self._cost_guard.record_actual(run_id, cost_usd)
        except CostCapExceeded as e:
            logger.warning(
                "cost_cap_exceeded_on_retry",
                run_id=run_id,
                error=str(e),
            )
            return ExtractorRunResult(
                envelope=envelope,
                input_tokens=prev_input_tokens + input_tokens,
                output_tokens=prev_output_tokens + output_tokens,
                cost_usd=total_cost,
                latency_ms=int((time.monotonic() - start_time) * 1000),
                retry_count=1,
                failed=True,
                error=str(e),
            )

        # Validate again
        validation_error = self._validate_envelope(envelope, item)
        if validation_error is not None:
            return None  # Second failure

        latency_ms = int((time.monotonic() - start_time) * 1000)

        logger.info(
            "extraction_succeeded_after_retry",
            extractor_run_id=run_id,
            candidates_count=len(envelope.candidates),
            dropped_count=len(envelope.dropped_signals),
            cost_usd=f"{total_cost:.6f}",
            latency_ms=latency_ms,
        )

        return ExtractorRunResult(
            envelope=envelope,
            input_tokens=prev_input_tokens + input_tokens,
            output_tokens=prev_output_tokens + output_tokens,
            cost_usd=total_cost,
            latency_ms=latency_ms,
            retry_count=1,
        )

    def _empty_envelope(self, item: QueueItem) -> ExtractionEnvelope:
        """Create an empty envelope for error/fallback cases."""
        return ExtractionEnvelope(
            extractor_run_id=item.extractor_run_id,
            model=item.model,
            prompt_version=item.prompt_version,
            schema_version=item.schema_version,
            window={
                "turn_ids": [t.turn_id for t in item.window],
                "size": len(item.window),
            },
            candidates=[],
            dropped_signals=[],
        )
