"""Single authoritative character reload / invalidation entry point.

Call ``reload_character`` whenever a UGC soul spec is created or updated.
It clears every in-process handle that caches soul-spec data so the next
request sees the new version without a service restart.

Handles invalidated in order:
1. Module-level SoulRegistry (registry.py module singleton)
2. Wiring-layer cached registry (wiring.py @lru_cache — belt-and-suspenders)
3. AnchorInjector pre-compiled skeletons (not on the live compose hot path,
   but reset for correctness in tests / drift worker)
4. character_content overlay cache (no-op today; extended by C5a)
"""

from __future__ import annotations

from typing import Optional

import structlog

from .character_content import invalidate as _invalidate_content
from .registry import SoulSpec, get_soul_registry

logger = structlog.get_logger()


def reload_character(character_id: str, spec: Optional[SoulSpec] = None) -> None:
    """Reload / invalidate all in-process caches for a single character.

    Args:
        character_id: The character whose caches should be cleared.
        spec: If provided, the new SoulSpec is registered into the module
              registry.  If None, the character is only invalidated (evicted).
    """
    # 1. Module-level registry
    registry = get_soul_registry()
    if spec is not None:
        registry.register_spec(spec, source="ugc")
        logger.info("reload_character_registered", character_id=character_id)
    else:
        registry.invalidate(character_id)
        logger.info("reload_character_invalidated", character_id=character_id)

    # 2. Wiring @lru_cache — belt-and-suspenders to evict the stale singleton
    try:
        from heart.api import wiring as _wiring

        if hasattr(_wiring, "get_soul_registry") and hasattr(
            _wiring.get_soul_registry, "cache_clear"
        ):
            _wiring.get_soul_registry.cache_clear()
    except Exception as exc:  # noqa: BLE001
        logger.warning("reload_character_wiring_cache_clear_failed", error=str(exc))

    # 3. AnchorInjector pre-compiled skeletons
    try:
        from heart.ss01_soul.anchor_injector import reset_anchor_injector

        reset_anchor_injector()
    except Exception as exc:  # noqa: BLE001
        logger.warning("reload_character_anchor_injector_reset_failed", error=str(exc))

    # 4. character_content overlay cache (no-op until C5a)
    _invalidate_content(character_id)

    logger.info("reload_character_complete", character_id=character_id, had_spec=spec is not None)
