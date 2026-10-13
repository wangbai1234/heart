#!/usr/bin/env python3
"""Owner-authorized launch check; does not assert specialist review completion.

The stricter check_locale_resources.py --release gate remains available for
fully specialist-reviewed releases. This launch binds actual owner authorization
to complete resources and the exact package, recording incomplete reviews.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from check_locale_resources import inspect_resources, read_json, resource_hash
from heart.localization.release import validate_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    records = read_json(args.package)
    receipt = read_json(args.receipt)
    validate_release(records, receipt)
    base = read_json(ROOT / "web/src/i18n/locales/en.json")
    for code in receipt["edition_counts"]:
        resources = read_json(ROOT / f"web/src/i18n/locales/{code}.json")
        missing, errors = inspect_resources(base, resources)
        if missing or errors or resource_hash(resources) != receipt["resource_hashes"].get(code):
            raise ValueError("Incomplete, invalid or stale authorized resources: " + code)
    print(json.dumps({"authorized_editions": len(records), "resource_version": receipt["resource_version"],
        "review_evidence": receipt["review_evidence"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
