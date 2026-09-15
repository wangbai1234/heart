#!/usr/bin/env python3
"""One-shot metrics refresh to apply new cold-start formula immediately.

Run this inside the backend container after deploying the new code:
  docker exec -it <backend-container> python /app/scripts/refresh_metrics_once.py

Or SSH into VPS and run:
  cd /path/to/heart && python backend/scripts/refresh_metrics_once.py
"""
import asyncio
import sys
import os

# Ensure we can import heart modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

async def main():
    from heart.api.wiring import _get_session_factory
    from heart.workers.character_metrics_worker import refresh_character_metrics
    from sqlalchemy import text

    factory = _get_session_factory()
    async with factory() as session:
        print("Running metrics refresh with new cold-start formula...")
        updated = await refresh_character_metrics(session)
        await session.commit()
        print(f"✅ Refreshed recommendation_score for {updated} characters\n")

        # Show batch 13 scores after refresh
        result = await session.execute(text("""
            SELECT id, recommendation_score, real_view_count, real_play_uv
            FROM characters
            WHERE id IN (
                'pei_jixing','lu_shijin','fu_chengyan','shen_zhixu','gu_yanshen','wen_li',
                'xiao_bochen','song_shiqi','ji_yan','chu_hansheng','huo_qingyin',
                'chen_muye','xie_linyuan','xiao_lin','ling_xiao',
                'ye_xiuyuan','xie_changan','shen_yueqing','jiang_yimo'
            )
            ORDER BY recommendation_score DESC
        """))
        print("Batch 13 characters after refresh:")
        print(f"{'id':20s} | {'score':>8s} | {'views':>8s} | {'play_uv':>8s}")
        print("-" * 55)
        for row in result.mappings():
            print(f"{row['id']:20s} | {row['recommendation_score']:>8.4f} | {row['real_view_count']:>8} | {row['real_play_uv']:>8}")

        # Compare with top old characters
        print("\n\nTop 5 old characters for comparison:")
        result2 = await session.execute(text("""
            SELECT id, recommendation_score, real_view_count
            FROM characters
            WHERE id NOT IN (
                'pei_jixing','lu_shijin','fu_chengyan','shen_zhixu','gu_yanshen','wen_li',
                'xiao_bochen','song_shiqi','ji_yan','chu_hansheng','huo_qingyin',
                'chen_muye','xie_linyuan','xiao_lin','ling_xiao',
                'ye_xiuyuan','xie_changan','shen_yueqing','jiang_yimo'
            )
            AND status = 'active'
            AND (owner_user_id IS NULL OR (visibility = 'public' AND review_status = 'approved'))
            ORDER BY recommendation_score DESC
            LIMIT 5
        """))
        print(f"{'id':20s} | {'score':>8s} | {'views':>8s}")
        print("-" * 45)
        for row in result2.mappings():
            print(f"{row['id']:20s} | {row['recommendation_score']:>8.4f} | {row['real_view_count']:>8}")

if __name__ == "__main__":
    asyncio.run(main())
