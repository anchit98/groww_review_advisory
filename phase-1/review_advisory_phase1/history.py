"""Archive weekly pulse outputs for week-over-week history."""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def archive_weekly_pulse(
    *,
    weekly_pulse_path: Path,
    phase2_metadata_path: Path | None,
    history_dir: Path,
    run_date: date,
) -> dict[str, str]:
    history_dir.mkdir(parents=True, exist_ok=True)
    week_key = run_date.isoformat()
    week_dir = history_dir / "weekly_pulse" / week_key
    week_dir.mkdir(parents=True, exist_ok=True)

    pulse_dest = week_dir / "weekly_pulse.json"
    shutil.copy2(weekly_pulse_path, pulse_dest)

    outputs: dict[str, str] = {"weekly_pulse": str(pulse_dest)}
    if phase2_metadata_path and phase2_metadata_path.exists():
        meta_dest = week_dir / "phase2_run_metadata.json"
        shutil.copy2(phase2_metadata_path, meta_dest)
        outputs["phase2_run_metadata"] = str(meta_dest)

    index_path = history_dir / "runs_index.json"
    index = _load_index(index_path)
    entry = {
        "week_ending": week_key,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "weekly_pulse_path": str(pulse_dest),
        "phase2_run_metadata_path": outputs.get("phase2_run_metadata"),
    }
    if phase2_metadata_path and phase2_metadata_path.exists():
        meta = json.loads(phase2_metadata_path.read_text(encoding="utf-8"))
        entry["phase2_run_id"] = meta.get("run_id")
        entry["status"] = meta.get("status")
        entry["reporting_window"] = meta.get("reporting_window")

    existing = [row for row in index.get("runs", []) if row.get("week_ending") != week_key]
    existing.append(entry)
    existing.sort(key=lambda row: row.get("week_ending", ""), reverse=True)
    index["runs"] = existing
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    outputs["runs_index"] = str(index_path)
    return outputs


def _load_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"runs": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"runs": []}
    payload.setdefault("runs", [])
    return payload
