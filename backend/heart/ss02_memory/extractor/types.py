"""
SS02 Memory LLM Extractor — Pydantic models (locked schema v1.0.0)

Matches docs/design/memory_extractor_schema.md exactly.
JSON Schema draft-07 enforced via Pydantic v2.

Author: 心屿团队
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ── Enums (closed) ────────────────────────────────────────────


class EntityType(str, Enum):
    SELF = "self"
    PET = "pet"
    FAMILY = "family"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    LOCATION = "location"
    POSSESSION = "possession"
    PREFERENCE = "preference"
    EVENT = "event"
    OTHER = "other"


class Attribute(str, Enum):
    NAME = "name"
    NICKNAME = "nickname"
    AGE = "age"
    COLOR = "color"
    BREED = "breed"
    OCCUPATION = "occupation"
    RELATION = "relation"
    LOCATION_RESIDENCE = "location_residence"
    LOCATION_ORIGIN = "location_origin"
    HOBBY = "hobby"
    DISLIKE = "dislike"
    HEALTH_CONDITION = "health_condition"
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    OTHER = "other"


class Kind(str, Enum):
    DISCLOSURE = "disclosure"
    RHETORIC = "rhetoric"
    QUESTION = "question"
    NEGATION = "negation"
    HYPOTHETICAL = "hypothetical"


class Operation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    SUPERSEDE = "supersede"
    SOFT_DELETE = "soft_delete"


class DroppedReason(str, Enum):
    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    OUT_OF_SCOPE_ENTITY = "out_of_scope_entity"
    OUT_OF_SCOPE_ATTRIBUTE = "out_of_scope_attribute"
    LOW_CONFIDENCE = "low_confidence"
    SARCASM_OR_RHETORIC = "sarcasm_or_rhetoric"
    DUPLICATE_OF_L3 = "duplicate_of_l3"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    OTHER = "other"


# ── Input types (not wire format) ─────────────────────────────


class TurnInput(BaseModel):
    """Single turn in the extraction window."""

    turn_id: int
    speaker: str  # "user" | "assistant"
    ts: str  # ISO timestamp
    text: str


class L3FactSnapshot(BaseModel):
    """L3 fact passed to the LLM for supersession/negation grounding."""

    fact_id: UUID
    entity_type: str
    entity_ref: Optional[str] = None
    attribute: str
    value: str
    confidence: float
    last_seen: str  # ISO date


class Hint(BaseModel):
    """Regex hint from fast encoder (advisory only)."""

    turn_id: int
    raw_phrase: str
    suspected_attribute: str


class QueueItem(BaseModel):
    """Work item for the extractor — one batch of turns to process."""

    extractor_run_id: UUID
    session_id: UUID
    window: list[TurnInput]
    l3_snapshot: list[L3FactSnapshot] = Field(default_factory=list)
    hints: list[Hint] = Field(default_factory=list)
    model: str = "deepseek-v4-flash"
    prompt_version: str = "1.0.0"
    schema_version: str = "1.0.0"


# ── Wire format (envelope) ────────────────────────────────────


class ExtractionCandidate(BaseModel):
    """Single candidate fact extracted by the LLM."""

    entity_type: EntityType
    attribute: Attribute
    value: str = Field(..., min_length=1, max_length=500)
    entity_ref: Optional[str] = Field(None, max_length=100)
    prior_value_id: Optional[UUID] = None
    source_turns: list[int] = Field(..., min_length=1, max_length=16)
    confidence: float = Field(..., ge=0.0, le=1.0)
    kind: Kind
    operation: Operation
    reasoning: str = Field(..., min_length=1, max_length=200)


class DroppedSignal(BaseModel):
    """Signal the LLM recognized but chose not to surface as a candidate."""

    turn_id: int
    raw_phrase: str = Field(..., min_length=1, max_length=500)
    reason: DroppedReason


class Window(BaseModel):
    """Window metadata echoed back in the envelope."""

    turn_ids: list[int] = Field(..., min_length=1, max_length=64)
    size: int = Field(..., ge=1, le=64)


class ExtractionEnvelope(BaseModel):
    """Top-level envelope emitted by the LLM Extractor (schema v1.0.0)."""

    extractor_run_id: UUID
    model: str = Field(..., min_length=1, max_length=100)
    prompt_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    window: Window
    candidates: list[ExtractionCandidate] = Field(default_factory=list, max_length=32)
    dropped_signals: list[DroppedSignal] = Field(default_factory=list, max_length=32)


# ── Result type ───────────────────────────────────────────────


class ExtractorRunResult(BaseModel):
    """Result of a single extractor run over a batch of QueueItems."""

    envelope: ExtractionEnvelope
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    retry_count: int = 0
    failed: bool = False
    error: Optional[str] = None
