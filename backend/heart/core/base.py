"""Shared SQLAlchemy DeclarativeBase for all subsystems.

All models should import Base from here instead of defining their own.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared base class for all SQLAlchemy models."""

    pass
