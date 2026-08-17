"""062 — Rename character tag 「纯洁」→「洁」.

Product direction (2026-08-17): the role tag 「纯洁」is shortened to 「洁」in the
discovery filter chips + the UGC create form's preset tags. Existing characters
carrying 「纯洁」in their JSONB ``characters.tags`` array must be rewritten so the
old label doesn't linger as an orphan custom tag that no chip matches.

Idempotent: rewrites every element equal to 「纯洁」to 「洁」in place; re-running is
a no-op once no 「纯洁」remains. Pure SQL over JSONB, no business imports.
"""

from __future__ import annotations

from alembic import op

revision = "062_rename_tag_chunjie_to_jie"
down_revision = "061_rename_fish_presets"
branch_labels = None
depends_on = None


def _rewrite(old: str, new: str) -> None:
    # Rebuild the tags array element-by-element, swapping `old` for `new`.
    # Guarded by a WHERE so only affected rows are touched (keeps the migration
    # cheap + the row's updated_at semantics clean).
    op.execute(
        """
        UPDATE characters
        SET tags = (
            SELECT COALESCE(jsonb_agg(
                CASE WHEN elem = to_jsonb('{old}'::text)
                     THEN to_jsonb('{new}'::text)
                     ELSE elem END
            ), '[]'::jsonb)
            FROM jsonb_array_elements(tags) AS elem
        )
        WHERE tags @> to_jsonb(ARRAY['{old}']::text[])
        """.format(old=old.replace("'", "''"), new=new.replace("'", "''"))
    )  # noqa: S608 — module-level constants only, no user input


def upgrade() -> None:
    _rewrite("纯洁", "洁")


def downgrade() -> None:
    _rewrite("洁", "纯洁")
