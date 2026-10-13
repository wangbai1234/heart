#!/usr/bin/env python3
"""Check draft resources; release mode requires full, reviewed coverage."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS = re.compile(r"{{\s*([^{}]+?)\s*}}")


def read_json(path: Path) -> dict:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate key in {path.name}: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def resource_hash(resources: dict) -> str:
    return hashlib.sha256(json.dumps(resources, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def inspect_resources(base: dict, resources: dict) -> tuple[list[str], list[str]]:
    missing = sorted(set(base) - set(resources))
    errors = [f"Unknown key: {key}" for key in sorted(set(resources) - set(base))]
    for key, value in resources.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Blank or non-string value: {key}")
        elif key in base and sorted(PLACEHOLDERS.findall(value)) != sorted(PLACEHOLDERS.findall(base[key])):
            errors.append(f"Placeholder mismatch: {key}")
    return missing, errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", nargs="+", default=[])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    registry = read_json(ROOT / "config/locales.json")
    folder = ROOT / "web/src/i18n/locales"
    base = read_json(folder / "en.json")
    codes = {row["code"] for row in registry["locales"]}
    if set(args.release) - codes:
        parser.error("Unregistered release locale")
    report = {}
    failures = []
    for row in registry["locales"]:
        code = row["code"]
        resources = read_json(folder / f"{code}.json")
        if code == "zh":
            resources = {**read_json(ROOT / "web/src/i18n/legacy.json"), **resources}
        missing, errors = inspect_resources(base, resources)
        digest = resource_hash(resources)
        report[code] = {"total": len(base), "translated": len(set(base) & set(resources)),
                        "missing": missing, "errors": errors, "resourceSha256": digest,
                        "status": row["status"]}
        print(f"{code}: {report[code]['translated']}/{len(base)} keys; {len(missing)} missing; {len(errors)} errors; {row['status']}")
        failures.extend(f"{code}: {error}" for error in errors)
        if missing and row["status"] != "draft":
            failures.append(f"{code}: non-draft resource has missing keys")
        if code in args.release:
            if missing or row["status"] not in {"reviewed", "live"}:
                failures.append(f"{code}: release requires complete reviewed resources")
            evidence_path = ROOT / f"config/locale-reviews/{code}.json"
            evidence = read_json(evidence_path) if evidence_path.exists() else {}
            if (evidence.get("resourceSha256") != digest
                    or not evidence.get("reviewer") or not evidence.get("reviewedAt")
                    or evidence.get("decision") != "approved"
                    or not all(evidence.get("checks", {}).get(check) is True for check in
                               ("nativeLanguage", "legal", "coreFlows", "modelOutput", "mobileLayout"))):
                failures.append(f"{code}: missing, stale or incomplete human review evidence")
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
