#!/usr/bin/env python3
"""Exit non-zero when a phase CLI result JSON reports a failed run status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FAIL_STATUSES = frozenset({"failed"})
OK_STATUSES = frozenset({"completed", "dry_run_prepared", "skipped_unchanged"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_file", type=Path, help="Path to phaseN_result.json stdout capture")
    parser.add_argument(
        "--phase",
        required=True,
        choices=("1", "2", "3"),
        help="Phase number for error messages",
    )
    parser.add_argument(
        "--allow-partial-success",
        action="store_true",
        help="Phase 3 only: exit 0 when status is partial_success (Doc OK, draft failed).",
    )
    args = parser.parse_args()

    if not args.result_file.exists():
        print(f"::error::Phase {args.phase} result file missing: {args.result_file}", file=sys.stderr)
        return 1

    payload = json.loads(args.result_file.read_text(encoding="utf-8"))
    status = (payload.get("metadata") or {}).get("status", "unknown")

    if status in FAIL_STATUSES:
        print(f"::error::Phase {args.phase} failed with status={status}", file=sys.stderr)
        return 1

    if status == "partial_success" and not args.allow_partial_success:
        print(
            f"::error::Phase {args.phase} partial_success (e.g. Doc OK, Gmail draft failed). "
            "Re-run Phase 3 or fix MCP.",
            file=sys.stderr,
        )
        return 1

    if status in OK_STATUSES:
        print(f"Phase {args.phase} status OK: {status}")
        return 0

    if status == "unknown":
        print(f"::error::Phase {args.phase} missing metadata.status in result JSON", file=sys.stderr)
        return 1

    print(f"::error::Phase {args.phase} unexpected status={status}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
