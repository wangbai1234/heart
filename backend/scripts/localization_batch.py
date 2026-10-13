"""Offline source×locale tasks. Never generates with or sends data to a model."""
import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from heart.core.config import settings
from heart.localization.batch import plan, validate, import_review


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "validate", "import-review"])
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--locales", nargs="+")
    parser.add_argument("--folder", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "plan":
        if not args.sources or not args.locales:
            parser.error("plan requires --sources and --locales")
        tasks = plan(read(args.sources), args.locales)
        args.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = args.folder / "tasks.json"
        if path.exists() and read(path) != tasks:
            raise ValueError("Existing plan differs; use a new folder")
        path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        path.chmod(0o600)
        print(f"Prepared {len(tasks)} tasks; provide one <task_id>.json candidate per task.")
        return
    tasks = read(args.folder / "tasks.json")
    # Never use unvalidated manifest strings as paths.
    for task in tasks:
        if task != plan([task["source"]], [task["locale"]])[0]:
            raise ValueError("Invalid task")
    candidates = [read(args.folder / (task["task_id"] + ".json")) for task in tasks]
    for task, candidate in zip(tasks, candidates, strict=True):
        validate(task, candidate, approved=args.action == "import-review")
    if args.action == "import-review":
        asyncio.run(apply(tasks, candidates))
    else:
        print(f"Validated {len(tasks)} complete drafts; human review still required.")


async def apply(tasks, candidates):
    url = make_url(settings.database_url)
    if url.host not in {"localhost", "127.0.0.1"} or url.database != "heart_review":
        raise ValueError("Only loopback heart_review is allowed")
    engine = create_async_engine(url)
    try:
        async with engine.begin() as db:
            ids = await import_review(db, tasks, candidates)
        print(f"Imported {len(ids)} private review copies; no production publication.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    main()
