#!/usr/bin/env python3
"""Seed data/warehouse from an existing Phase 1 run directory."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase1-run-dir",
        type=Path,
        required=True,
        help="e.g. phase-1/output/phase1-2026-05-11-f0813bdc",
    )
    parser.add_argument(
        "--warehouse-dir",
        type=Path,
        default=Path("data/warehouse"),
    )
    args = parser.parse_args()

    src_reviews = args.phase1_run_dir / "normalized_reviews.json"
    src_meta = args.phase1_run_dir / "run_metadata.json"
    if not src_reviews.exists():
        raise SystemExit(f"Missing {src_reviews}")

    args.warehouse_dir.mkdir(parents=True, exist_ok=True)
    reviews = json.loads(src_reviews.read_text(encoding="utf-8"))
    shutil.copy2(src_reviews, args.warehouse_dir / "normalized_reviews.json")

    reporting = {}
    if src_meta.exists():
        reporting = json.loads(src_meta.read_text(encoding="utf-8")).get("reporting_window", {})

    warehouse_meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "first_populated_at": datetime.now(timezone.utc).isoformat(),
        "seeded_from": str(args.phase1_run_dir),
        "rolling_window_weeks": reporting.get("lookback_weeks", 8),
        "reporting_window": reporting,
        "counts": {"total_reviews": len(reviews), "new_reviews_this_run": len(reviews), "pruned_outside_window": 0},
        "bootstrap": True,
        "note": "Seeded from prior Phase 1 run before gap-fill fetch.",
    }
    (args.warehouse_dir / "warehouse_metadata.json").write_text(
        json.dumps(warehouse_meta, indent=2),
        encoding="utf-8",
    )
    print(f"Seeded warehouse with {len(reviews)} reviews from {args.phase1_run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
