"""story heat values

Revision ID: 045_story_heat_values
Revises: 044_story_playtime
Create Date: 2026-07-23

"""
from alembic import op
import random

# revision identifiers, used by Alembic.
revision = '045_story_heat_values'
down_revision = '044_story_playtime'
branch_labels = None
depends_on = None


def upgrade():
    """
    设定探索页剧情推荐的初始热度值：
    - 4个精选剧情：9999-15000之间的随机热度（用于推荐 banner）
    - 其他剧情：500-8000之间的随机热度

    这是一次性的初始化；后续热度由真实 play_count 驱动。
    """
    # 4个高热度精选剧情
    featured_slugs = [
        '人外＊饲养指南',
        '无限流？好玩的恐怖游戏而已',
        'Omega总想反攻',
        '当我暗恋的哥哥朋友成为我的顶头上司',
    ]

    conn = op.get_bind()

    # 设置精选剧情的高热度并标记为 featured
    for slug in featured_slugs:
        heat = random.randint(9999, 15000)
        conn.execute(f"""
            UPDATE story_scenarios
            SET play_count = {heat}, is_featured = true
            WHERE slug = '{slug}'
        """)

    # 其他剧情设置为中等热度（排除已设置的精选）
    # 使用随机函数直接在 SQL 中生成，避免 Python 循环
    conn.execute("""
        UPDATE story_scenarios
        SET play_count = floor(random() * 7500 + 500)::int
        WHERE slug NOT IN (
            '人外＊饲养指南',
            '无限流？好玩的恐怖游戏而已',
            'Omega总想反攻',
            '当我暗恋的哥哥朋友成为我的顶头上司'
        )
        AND status = 'published'
    """)


def downgrade():
    """重置所有热度为0"""
    op.execute("UPDATE story_scenarios SET play_count = 0, is_featured = false")
