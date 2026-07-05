"""One-time cleanup of dirty identity memories (P0-3, the "什么吗" bug).

Historical L3 FactNodes / L4 IdentityMemories were polluted when the LLM
extractor mis-tagged an interrogative ("我叫什么吗") as a name disclosure,
which slipped past the resolver and (for L3) later got promoted to L4.

The resolver now rejects such values deterministically
(`is_implausible_identity_value`), so this only cleans *existing* rows.

M-1 compliance: nothing is physically deleted.
  - L4 rows are logically demoted (`demoted_at` / `demotion_reason` + audit_log).
  - Source / active L3 rows are marked `is_corrected` + `do_not_recall` + inactive.

Usage (dry-run prints what would change, writes nothing):
    python -m heart.scripts.cleanup_dirty_l4
Apply the changes:
    python -m heart.scripts.cleanup_dirty_l4 --apply

Author: 心屿团队
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from heart.ss02_memory.extractor.resolver import is_implausible_identity_value
from heart.ss02_memory.extractor.types import Attribute
from heart.ss02_memory.models import FactNode, IdentityMemory

logger = structlog.get_logger()

# L4.key / L3.predicate strings that map to identity attributes we validate.
_IDENTITY_KEYS = {Attribute.NAME.value, Attribute.NICKNAME.value}


def _attr_for(key: str) -> Attribute | None:
    """Map an L4 key / L3 predicate string to an Attribute, or None if not identity."""
    try:
        attr = Attribute(key)
    except ValueError:
        return None
    return attr if attr in {Attribute.NAME, Attribute.NICKNAME} else None


async def _cleanup(apply: bool) -> tuple[int, int]:
    """Return (l4_demoted, l3_corrected) counts. Writes only when apply=True."""
    from heart.api.wiring import _get_session_factory

    factory = _get_session_factory()
    now = datetime.now(timezone.utc)
    l4_count = 0
    l3_count = 0

    async with factory() as db:
        # ── L4 IdentityMemory ──
        l4_rows = (
            (
                await db.execute(
                    select(IdentityMemory).where(
                        IdentityMemory.key.in_(_IDENTITY_KEYS),
                        IdentityMemory.demoted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in l4_rows:
            attr = _attr_for(row.key)
            if attr is None or not is_implausible_identity_value(attr, row.value):
                continue
            l4_count += 1
            logger.info(
                "dirty_l4_found",
                id=str(row.id),
                key=row.key,
                value=row.value,
                source_fact=str(row.promoted_from_fact_id) if row.promoted_from_fact_id else None,
                will_apply=apply,
            )
            if apply:
                row.demoted_at = now
                row.demotion_reason = "dirty_interrogative_value_cleanup (P0-3)"
                row.audit_log = list(row.audit_log or []) + [
                    {
                        "at": now.isoformat(),
                        "action": "demote",
                        "reason": "implausible identity value (interrogative/pronoun)",
                    }
                ]
                # Correct the source L3 fact so it can never re-promote.
                if row.promoted_from_fact_id is not None:
                    src = await db.get(FactNode, row.promoted_from_fact_id)
                    if src is not None:
                        src.is_corrected = True
                        src.do_not_recall = True
                        src.is_active = False

        # ── L3 FactNode (active, identity predicate, implausible object) ──
        l3_rows = (
            (
                await db.execute(
                    select(FactNode).where(
                        FactNode.predicate.in_(_IDENTITY_KEYS),
                        FactNode.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        for fact in l3_rows:
            attr = _attr_for(fact.predicate)
            if attr is None or not is_implausible_identity_value(attr, fact.object):
                continue
            l3_count += 1
            logger.info(
                "dirty_l3_found",
                id=str(fact.id),
                predicate=fact.predicate,
                object=fact.object,
                will_apply=apply,
            )
            if apply:
                fact.is_corrected = True
                fact.do_not_recall = True
                fact.is_active = False

        if apply:
            await db.commit()

    return l4_count, l3_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean dirty interrogative identity memories.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the changes. Without this flag the script is a dry-run.",
    )
    args = parser.parse_args()

    l4, l3 = asyncio.run(_cleanup(args.apply))
    mode = "APPLIED" if args.apply else "DRY-RUN (no writes)"
    print(f"[{mode}] dirty L4 demoted: {l4}, dirty L3 corrected: {l3}")


if __name__ == "__main__":
    main()
