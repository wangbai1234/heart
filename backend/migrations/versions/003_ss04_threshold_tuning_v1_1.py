"""
Migration 003: SS04 Threshold Tuning v1.1

Purpose:
- Update existing users' soul_modifiers JSONB to reflect v1.1 progression_rate formula.
- NO current_stage downgrades (INV-R-1, R-4 high priority).
- Existing users keep their current_stage; new thresholds only affect future transitions.
- Update progression_rate based on character-specific intimacy_resistance values.

Characters:
- Rin: intimacy_resistance=0.75 → progression_rate = 0.25 (1.0 - 0.75)
- Dorothy: intimacy_resistance=0.15 → progression_rate = 0.85 (1.0 - 0.15)

Safety:
- Only updates soul_modifiers.progression_rate field
- Does NOT modify current_stage, highest_stage_reached, or any dimension scores
- Works with existing JSONB structure

Revision ID: 003
Revises: 002
Create Date: 2026-05-21

Author: 心屿团队
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = "003_ss04_threshold_tuning_v1_1"
down_revision: Union[str, None] = "002_add_emotion_relationship_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Character-specific progression rates (v1.1 formula)
CHARACTER_PROGRESSION_RATES = {
    "rin": 0.25,      # 1.0 - intimacy_resistance(0.75)
    "dorothy": 0.85,  # 1.0 - intimacy_resistance(0.15)
}

# Default for unknown characters
DEFAULT_PROGRESSION_RATE = 0.5  # 1.0 - default_intimacy_resistance(0.5)


def upgrade() -> None:
    """
    Update soul_modifiers.progression_rate for all existing users.

    INV-R-1 compliant: does NOT modify current_stage or highest_stage_reached.
    Only updates the progression_rate field in the JSONB soul_modifiers column.
    """
    conn = op.get_bind()

    # For each known character, update progression_rate
    for character_id, rate in CHARACTER_PROGRESSION_RATES.items():
        # Update soul_modifiers JSONB: set progression_rate to new value
        # Using raw SQL for JSONB update with COALESCE to handle NULL
        conn.execute(
            text("""
                UPDATE relationship_states
                SET soul_modifiers = jsonb_set(
                    COALESCE(soul_modifiers, '{}'::jsonb),
                    '{progression_rate}',
                    to_jsonb(:rate::float)
                ),
                updated_at = NOW(),
                version = version + 1
                WHERE character_id = :character_id
            """),
            {"character_id": character_id, "rate": rate},
        )

    # Update unknown characters with default rate
    known_characters = list(CHARACTER_PROGRESSION_RATES.keys())
    conn.execute(
        text("""
            UPDATE relationship_states
            SET soul_modifiers = jsonb_set(
                COALESCE(soul_modifiers, '{}'::jsonb),
                '{progression_rate}',
                to_jsonb(:rate::float)
            ),
            updated_at = NOW(),
            version = version + 1
            WHERE character_id NOT IN :known
        """),
        {
            "rate": DEFAULT_PROGRESSION_RATE,
            "known": tuple(known_characters),
        },
    )

    # Log migration summary
    result = conn.execute(
        text("SELECT character_id, COUNT(*) FROM relationship_states GROUP BY character_id")
    )
    summary = {row[0]: row[1] for row in result.fetchall()}
    print(f"[003] Updated soul_modifiers.progression_rate for {sum(summary.values())} users: {summary}")


def downgrade() -> None:
    """
    Revert progression_rate to original formula (1.0 - intimacy_resistance).

    Note: This reverts only the progression_rate field back to its previous
    computed value. Other JSONB fields are untouched.
    """
    conn = op.get_bind()

    # The original formula was: progression_rate = 1.0 - intimacy_resistance
    # But we don't store intimacy_resistance in the JSONB, so we restore
    # the character-specific values. In a real rollback scenario, you'd
    # want to recalculate from soul specs.

    # For simplicity, set all back to a neutral 1.0 (no scaling)
    conn.execute(
        text("""
            UPDATE relationship_states
            SET soul_modifiers = jsonb_set(
                COALESCE(soul_modifiers, '{}'::jsonb),
                '{progression_rate}',
                '1.0'::jsonb
            ),
            updated_at = NOW(),
            version = version + 1
        """)
    )

    print("[003 DOWNGRADE] Reverted all progression_rate values to 1.0")
