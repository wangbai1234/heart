"""Deduplicate L3 FactNode rows that share a canonical predicate.

Path A (memory_encoder.py) previously stored raw LLM-generated predicates
(e.g. "worries_about" and "concerned_about") as separate rows.  After
predicate_vocab.py is deployed, new writes will normalise predicates so
synonyms converge; this script merges the pre-existing duplicate rows.

Merge logic (per user_id, character_id):
  1. Load all is_active=True facts.
  2. Group by (subject, normalize_predicate(predicate)).
  3. Within each group, keep the row with the highest (confidence,
     confirmation_count) as the survivor; soft-delete the rest.
  4. Survivor: write canonical predicate, accumulate confirmation_count /
     mention_count, refresh semantic_vector with build_embedding_text.
  5. Losers: is_active=False, superseded_by_id=survivor.id.

Usage:
    python -m heart.scripts.dedupe_facts            # dry-run
    python -m heart.scripts.dedupe_facts --apply    # write to DB

Author: 心屿团队
"""

from __future__ import annotations

import argparse
import asyncio

import structlog
from sqlalchemy import select

from heart.ss02_memory.models import FactNode
from heart.ss02_memory.predicate_vocab import build_embedding_text, normalize_predicate

logger = structlog.get_logger()


async def _embed(embedder, subject: str, predicate: str, object_: str):
    try:
        return await embedder.embed_query(build_embedding_text(subject, predicate, object_))
    except Exception as e:
        logger.warning("embed_failed", error=str(e))
        return None


async def _run(apply: bool) -> dict[str, int]:
    from heart.api.wiring import _get_session_factory, get_embedding_service

    embedder = get_embedding_service()
    factory = _get_session_factory()

    stats = {"groups_scanned": 0, "survivors": 0, "soft_deleted": 0, "re_embedded": 0}

    async with factory() as db:
        facts = (
            (await db.execute(select(FactNode).where(FactNode.is_active.is_(True)))).scalars().all()
        )

        # Group by (user_id, character_id, subject, canonical_predicate)
        buckets: dict[tuple, list[FactNode]] = {}
        for f in facts:
            key = (f.user_id, f.character_id, f.subject, normalize_predicate(f.predicate))
            buckets.setdefault(key, []).append(f)

        for (user_id, char_id, subject, canonical_pred), group in buckets.items():
            stats["groups_scanned"] += 1
            if len(group) == 1:
                # Single row — just ensure predicate is canonical and embedding is fresh.
                f = group[0]
                if apply and (f.predicate != canonical_pred or f.semantic_vector is None):
                    f.predicate = canonical_pred
                    if embedder:
                        f.semantic_vector = await _embed(
                            embedder, f.subject, canonical_pred, f.object
                        )
                        stats["re_embedded"] += 1
                stats["survivors"] += 1
                continue

            # Multiple rows for same canonical predicate — pick survivor.
            group.sort(key=lambda r: (r.confidence or 0, r.confirmation_count or 0), reverse=True)
            survivor = group[0]
            losers = group[1:]

            logger.info(
                "merge_group",
                user_id=str(user_id),
                character_id=char_id,
                subject=subject,
                canonical_pred=canonical_pred,
                survivor_id=str(survivor.id),
                loser_count=len(losers),
                apply=apply,
            )

            if apply:
                # Update survivor
                survivor.predicate = canonical_pred
                survivor.confirmation_count = (survivor.confirmation_count or 0) + sum(
                    (r.confirmation_count or 0) for r in losers
                )
                survivor.mention_count = (survivor.mention_count or 0) + sum(
                    (r.mention_count or 0) for r in losers
                )
                if embedder:
                    survivor.semantic_vector = await _embed(
                        embedder, survivor.subject, canonical_pred, survivor.object
                    )
                    stats["re_embedded"] += 1

                # Soft-delete losers
                for loser in losers:
                    loser.is_active = False
                    loser.superseded_by_id = survivor.id

            stats["survivors"] += 1
            stats["soft_deleted"] += len(losers)

        if apply:
            await db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate synonym-predicate L3 FactNode rows.")
    parser.add_argument("--apply", action="store_true", help="Write changes (default dry-run).")
    args = parser.parse_args()

    stats = asyncio.run(_run(args.apply))
    mode = "APPLIED" if args.apply else "DRY-RUN (no writes)"
    print(
        f"[{mode}] groups_scanned={stats['groups_scanned']}, "
        f"survivors={stats['survivors']}, "
        f"soft_deleted={stats['soft_deleted']}, "
        f"re_embedded={stats['re_embedded']}"
    )


if __name__ == "__main__":
    main()
