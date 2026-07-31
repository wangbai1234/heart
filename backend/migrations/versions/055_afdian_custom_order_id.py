"""Add custom_order_id to afdian_orders for binding code matching.

爱发电 order/create 页支持 URL 参数 custom_order_id,webhook 回调时原样带回。
此列让订单认领优先用 custom_order_id 精确匹配,免去用户填备注环节。
回退路径(remark 模糊匹配)保持不变,不破坏既有订单流程。

Revision ID: 055_afdian_custom_order_id
Revises: 054_opening_history
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "055_afdian_custom_order_id"
down_revision = "054_opening_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # custom_order_id: 前端下单深链里带的绑定码,webhook 原样返回
    op.execute(
        """
        ALTER TABLE afdian_orders
        ADD COLUMN IF NOT EXISTS custom_order_id VARCHAR(64)
        """
    )
    # 加速精确匹配 binding code(现有 remark 模糊匹配保留向下兼容)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_binding_codes_code
        ON user_binding_codes (code) WHERE used_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_binding_codes_code")
    op.execute("ALTER TABLE afdian_orders DROP COLUMN IF EXISTS custom_order_id")
