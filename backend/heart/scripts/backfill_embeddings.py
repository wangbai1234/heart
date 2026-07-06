"""One-time backfill of semantic_vector for existing memories (PR4d).

Semantic recall only works on rows that have an embedding. Rows written before
PR4c/PR4d have semantic_vector = NULL. This script embeds:
  - L2 EpisodicMemory.episode_summary  (where semantic_vector IS NULL)
  - L3 FactNode.literal_text           (where semantic_vector IS NULL, is_active)

Requires EMBEDDING_API_KEY (else exits — nothing to embed with).

Usage (dry-run counts, no writes / no API calls):
    python -m heart.scripts.backfill_embeddings
Apply (embeds + writes, in batches):
    python -m heart.scripts.backfill_embeddings --apply --batch 64

Author: 心屿团队
"""

from __future__ import annotations

import argparse
import asyncio

import structlog
from sqlalchemy import select

from heart.ss02_memory.models import EpisodicMemory, FactNode

logger = structlog.get_logger()


async def _backfill_table(session, embedder, rows, text_of, apply: bool, batch: int) -> int:
    """Embed `rows` in batches and assign semantic_vector. Returns count updated."""
    updated = 0
    for start in range(0, len(rows), batch):
        chunk = rows[start : start + batch]
        texts = [text_of(r) for r in chunk]
        if apply:
            vectors = await embedder.embed_texts(texts)
            for row, vec in zip(chunk, vectors, strict=True):
                row.semantic_vector = vec
        updated += len(chunk)
    return updated


async def _run(apply: bool, batch: int) -> tuple[int, int]:
    from heart.api.wiring import _get_session_factory, get_embedding_service

    embedder = get_embedding_service()
    if embedder is None:
        print("[skip] no EMBEDDING_API_KEY configured — nothing to backfill with.")
        return (0, 0)

    factory = _get_session_factory()
    async with factory() as db:
        episodes = (
            (
                await db.execute(
                    select(EpisodicMemory).where(EpisodicMemory.semantic_vector.is_(None))
                )
            )
            .scalars()
            .all()
        )
        facts = (
            (
                await db.execute(
                    select(FactNode).where(
                        FactNode.semantic_vector.is_(None),
                        FactNode.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )

        logger.info("backfill_scope", l2=len(episodes), l3=len(facts), apply=apply)

        l2 = await _backfill_table(
            db, embedder, episodes, lambda e: e.episode_summary or "", apply, batch
        )
        l3 = await _backfill_table(
            db, embedder, facts, lambda f: f.literal_text or "", apply, batch
        )

        if apply:
            await db.commit()

    return (l2, l3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill semantic_vector for L2/L3 memories.")
    parser.add_argument("--apply", action="store_true", help="Embed and write (default dry-run).")
    parser.add_argument("--batch", type=int, default=64, help="Embedding batch size.")
    args = parser.parse_args()

    l2, l3 = asyncio.run(_run(args.apply, args.batch))
    mode = "APPLIED" if args.apply else "DRY-RUN (no writes / no API calls)"
    print(f"[{mode}] L2 episodes: {l2}, L3 facts: {l3}")


if __name__ == "__main__":
    main()
