"""052 — Deactivate retired built-in characters.

Revision ID: 052_deactivate_retired_characters
Revises: 051_user_password_hash
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "052_deactivate_retired_characters"
down_revision = "051_user_password_hash"
branch_labels = None
depends_on = None


RETIRED_CHARACTER_IDS = (
    "jiang_yanzhou",
    "xingye",
    "zhu_xing",
    "murong_jin",
    "mu_beihan",
    "lu_chen",
    "wen_yining",
    "lin_shen",
    "xiao_yao",
    "shen_guhong",
    "gu_han",
    "bo_jin",
    "jiang_wan",
    "xuan_ye",
    "cang_wu",
    "shi_yue",
    "ye_bai",
    "luo_yin",
    "ye_lan",
    "bai_zhi",
    "pei_shen",
    "xie_yuntang",
)


def upgrade() -> None:
    ids = ", ".join(f"'{cid}'" for cid in RETIRED_CHARACTER_IDS)
    op.execute(
        f"""
        UPDATE characters
        SET status = 'disabled'
        WHERE owner_user_id IS NULL
          AND id IN ({ids})
        """
    )


def downgrade() -> None:
    ids = ", ".join(f"'{cid}'" for cid in RETIRED_CHARACTER_IDS)
    op.execute(
        f"""
        UPDATE characters
        SET status = 'active'
        WHERE owner_user_id IS NULL
          AND id IN ({ids})
        """
    )
