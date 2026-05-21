#!/usr/bin/env python3
"""Write a GitHub Actions job summary from phase result JSON files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _load(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _status_badge(status: str) -> str:
    if status in ("completed", "skipped_unchanged"):
        return f"✅ `{status}`"
    if status in ("partial_success", "dry_run_prepared"):
        return f"⚠️ `{status}`"
    if status == "failed":
        return f"❌ `{status}`"
    return f"`{status}`"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase1", type=Path, default=None)
    parser.add_argument("--phase2", type=Path, default=None)
    parser.add_argument("--phase3", type=Path, default=None)
    parser.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    args = parser.parse_args()

    lines = [
        "## Weekly Review Advisory",
        "",
        f"- **Workflow run:** `{args.github_run_id}`",
        "",
    ]

    for label, path in (
        ("Phase 1", args.phase1),
        ("Phase 2", args.phase2),
        ("Phase 3", args.phase3),
    ):
        payload = _load(path)
        meta = payload.get("metadata") or {}
        paths = payload.get("output_paths") or {}
        status = meta.get("status", "n/a")
        lines.append(f"### {label}")
        lines.append(f"- Status: {_status_badge(status)}")
        if paths.get("run_directory"):
            lines.append(f"- Output: `{paths['run_directory']}`")
        if meta.get("reporting_window"):
            window = meta["reporting_window"]
            lines.append(
                f"- Reporting window: `{window.get('start_date')}` → `{window.get('end_date')}`"
            )
        if meta.get("publication"):
            pub = meta["publication"]
            for key in ("google_doc", "gmail_draft"):
                block = pub.get(key) or {}
                if block.get("status"):
                    lines.append(f"- {key}: `{block.get('status')}`")
        warnings = meta.get("warnings") or []
        if warnings:
            lines.append(f"- Warnings: {len(warnings)} (see `run_metadata.json` in artifacts)")
        lines.append("")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
