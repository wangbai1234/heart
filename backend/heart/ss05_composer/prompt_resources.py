"""Versioned application prompt text; interpolate source data only after selection.

New reply languages can add a catalog with the same keys. Missing catalogs use
English application instructions; disabled/Chinese replies retain Chinese text.
No runtime translation calls and no rewriting of creator or user data.
"""

import json
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).with_name("prompts")
_CATALOGS = frozenset(p.stem for p in _ROOT.glob("*.json"))


@lru_cache(maxsize=None)
def prompt_catalog(language: str) -> dict[str, str]:
    code = language if language in _CATALOGS else "en"
    return json.loads((_ROOT / f"{code}.json").read_text(encoding="utf-8"))


def prompt_text(language: str, key: str, **values: str) -> str:
    return prompt_catalog(language)[key].format(**values)
