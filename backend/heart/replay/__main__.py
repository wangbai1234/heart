"""python -m heart.replay entry point."""

import asyncio
import sys

from .cli import main as _main

if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
