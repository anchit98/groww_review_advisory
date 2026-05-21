#!/usr/bin/env python3
"""Update data/history/runs_index.json after a successful weekly pipeline run."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"runs": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"runs": []}
    payload.setdefault("runs", [])
    return payload


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _publication_from_phase3(meta: dict[str, Any]) -> dict[str, str]:
    publication = meta.get("publication") or {}
    doc = (publication.get("google_doc") or {}).get("status", "unknown")
    mail = (publication.get("gmail_draft") or {}).get("status", "unknown")
    return {"google_doc": doc, "gmail_draft": mail}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", required=True, help="Week-ending date YYYY-MM-DD")
    parser.add_argument("--phase2-metadata", type=Path, required=True)
    parser.add_argument("--phase3-metadata", type=Path, default=None)
    parser.add_argument("--weekly-pulse", type=Path, required=True)
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=Path("data/history"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    history_dir = (repo_root / args.history_dir).resolve()
    week_key = args.run_date
    week_dir = history_dir / "weekly_pulse" / week_key

    phase2_meta = json.loads(args.phase2_metadata.read_text(encoding="utf-8"))
    phase2_dir = args.phase2_metadata.resolve().parent
    quote_candidates_src = phase2_dir / "quote_candidates.json"
    phase3_meta: dict[str, Any] | None = None
    if args.phase3_metadata and args.phase3_metadata.exists():
        phase3_meta = json.loads(args.phase3_metadata.read_text(encoding="utf-8"))

    entry: dict[str, Any] = {
        "week_ending": week_key,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "weekly_pulse_path": _rel(args.weekly_pulse.resolve(), repo_root),
        "phase2_run_metadata_path": _rel(args.phase2_metadata.resolve(), repo_root),
        "phase2_run_id": phase2_meta.get("run_id"),
        "status": phase2_meta.get("status", "unknown"),
        "reporting_window": phase2_meta.get("reporting_window"),
    }

    pulse_dest = week_dir / "weekly_pulse.json"
    if pulse_dest.exists():
        entry["weekly_pulse_path"] = _rel(pulse_dest, repo_root)
    meta_dest = week_dir / "phase2_run_metadata.json"
    if meta_dest.exists():
        entry["phase2_run_metadata_path"] = _rel(meta_dest, repo_root)

    if quote_candidates_src.exists():
        quote_dest = week_dir / "quote_candidates.json"
        shutil.copy2(quote_candidates_src, quote_dest)
        entry["quote_candidates_path"] = _rel(quote_dest, repo_root)

    consolidation_src = phase2_dir / "consolidation_response.json"
    if consolidation_src.exists():
        consolidation_dest = week_dir / "consolidation_response.json"
        shutil.copy2(consolidation_src, consolidation_dest)
        entry["consolidation_response_path"] = _rel(consolidation_dest, repo_root)

    if phase3_meta:
        entry["phase3_run_id"] = phase3_meta.get("run_id")
        entry["phase3_status"] = phase3_meta.get("status")
        entry["google_doc_url"] = phase3_meta.get("google_doc_url")
        entry["publication"] = _publication_from_phase3(phase3_meta)
        phase3_dest = week_dir / "phase3_run_metadata.json"
        if phase3_dest.exists():
            entry["phase3_run_metadata_path"] = _rel(phase3_dest, repo_root)
        note_dest = week_dir / "weekly_note.md"
        if note_dest.exists():
            entry["weekly_note_path"] = _rel(note_dest, repo_root)
        draft_dest = week_dir / "email_draft.txt"
        if draft_dest.exists():
            entry["email_draft_path"] = _rel(draft_dest, repo_root)

    index_path = history_dir / "runs_index.json"
    index = _load_index(index_path)
    runs = [row for row in index["runs"] if row.get("week_ending") != week_key]
    runs.append(entry)
    runs.sort(key=lambda row: row.get("week_ending", ""), reverse=True)
    index["runs"] = runs
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Updated {index_path} for week {week_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
