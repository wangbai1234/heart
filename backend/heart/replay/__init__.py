"""replay/__init__.py — SQLAlchemy model for replay_snapshots table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ReplaySnapshot(Base):
    """Persisted per-turn prompt bundle for replay/debug inspection."""

    __tablename__ = "replay_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turn_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(String(255), nullable=False)
    character_id = Column(String(255), nullable=False)

    prompt_bundle = Column(JSONB, nullable=False)
    raw_response = Column(Text, nullable=False)
    final_response = Column(Text, nullable=False)

    latency_ms = Column(Integer)
    model_name = Column(String(100))
    token_count = Column(Integer)

    anti_pattern_hits = Column(JSONB, nullable=False, default=list)
    blocked = Column(Boolean, nullable=False, default=False)

    critic_score = Column(Numeric(3, 2))
    critic_feedback = Column(Text)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
