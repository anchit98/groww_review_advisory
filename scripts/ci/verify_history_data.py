#!/usr/bin/env python3
"""Fail Render/CI builds when weekly history data is missing from the deploy tree."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = REPO_ROOT / "data" / "history" / "runs_index.json"


def main() -> int:
    if not INDEX_PATH.exists():
        print(
            f"ERROR: {INDEX_PATH} is missing. "
            "Commit data/history/ and deploy from the repository root (not backend-only).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: found runs index at {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
