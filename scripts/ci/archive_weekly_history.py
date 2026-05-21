#!/usr/bin/env python3
"""Archive Phase 2 weekly_pulse.json into data/history for week-over-week retention."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "phase-1"))

from review_advisory_phase1.history import archive_weekly_pulse  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weekly-pulse", type=Path, required=True)
    parser.add_argument("--phase2-metadata", type=Path, default=None)
    parser.add_argument("--run-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=_REPO_ROOT / "data" / "history",
    )
    args = parser.parse_args()

    outputs = archive_weekly_pulse(
        weekly_pulse_path=args.weekly_pulse,
        phase2_metadata_path=args.phase2_metadata,
        history_dir=args.history_dir,
        run_date=args.run_date,
    )
    print(f"Archived weekly pulse for {args.run_date.isoformat()}")
    for key, path in outputs.items():
        print(f"  {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
