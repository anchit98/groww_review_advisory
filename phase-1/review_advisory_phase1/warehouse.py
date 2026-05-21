"""Rolling review warehouse for incremental weekly ingestion."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .pipeline import CanonicalReview, PipelineRunResult


DEFAULT_ROLLING_WINDOW_WEEKS = 8


def warehouse_paths(warehouse_dir: Path) -> dict[str, Path]:
    root = Path(warehouse_dir)
    return {
        "root": root,
        "reviews": root / "normalized_reviews.json",
        "metadata": root / "warehouse_metadata.json",
    }


def load_review_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Warehouse reviews file must be a JSON array: {path}")
    return payload


def dict_to_canonical(row: dict[str, Any]) -> CanonicalReview:
    ingested_raw = row.get("ingested_at", "")
    if isinstance(ingested_raw, str) and ingested_raw:
        ingested_at = datetime.fromisoformat(ingested_raw.replace("Z", "+00:00"))
    else:
        ingested_at = datetime.now(timezone.utc)
    return CanonicalReview(
        source=str(row["source"]),
        rating=int(row["rating"]),
        title=str(row.get("title") or ""),
        review_text=str(row["review_text"]),
        review_date=date.fromisoformat(str(row["review_date"])),
        language=str(row.get("language") or "en"),
        ingested_at=ingested_at,
        review_id_hash=str(row["review_id_hash"]),
    )


def merge_incremental_run(
    *,
    run_result: PipelineRunResult,
    run_date: date,
    warehouse_dir: Path,
    rolling_window_weeks: int = DEFAULT_ROLLING_WINDOW_WEEKS,
) -> PipelineRunResult:
    """
    Merge this run's newly normalized reviews into the warehouse, prune outside
    the rolling window, and rewrite the run outputs to the merged corpus.
    """
    paths = warehouse_paths(warehouse_dir)
    paths["root"].mkdir(parents=True, exist_ok=True)

    existing_rows = load_review_dicts(paths["reviews"])
    index: dict[str, dict[str, Any]] = {
        str(row["review_id_hash"]): row for row in existing_rows if row.get("review_id_hash")
    }

    new_hashes: list[str] = []
    updated_count = 0
    for review in run_result.normalized_reviews:
        payload = review.to_dict()
        key = review.review_id_hash
        if key in index:
            updated_count += 1
        else:
            new_hashes.append(key)
        index[key] = payload

    window_end = run_date
    window_start = window_end - timedelta(weeks=rolling_window_weeks)
    pruned_hashes: list[str] = []
    merged_rows: list[dict[str, Any]] = []
    for row in index.values():
        review_date = date.fromisoformat(str(row["review_date"]))
        if review_date < window_start or review_date > window_end:
            pruned_hashes.append(str(row["review_id_hash"]))
            continue
        merged_rows.append(row)

    merged_rows.sort(
        key=lambda row: (row["review_date"], row["source"], row["review_id_hash"]),
    )
    merged_reviews = [dict_to_canonical(row) for row in merged_rows]

    warehouse_meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rolling_window_weeks": rolling_window_weeks,
        "reporting_window": {
            "start_date": window_start.isoformat(),
            "end_date": window_end.isoformat(),
            "lookback_weeks": rolling_window_weeks,
        },
        "counts": {
            "total_reviews": len(merged_rows),
            "new_reviews_this_run": len(new_hashes),
            "updated_existing": updated_count,
            "pruned_outside_window": len(pruned_hashes),
        },
        "last_run_id": run_result.metadata.get("run_id"),
    }
    if paths["metadata"].exists():
        prior = json.loads(paths["metadata"].read_text(encoding="utf-8"))
        warehouse_meta["first_populated_at"] = prior.get("first_populated_at") or prior.get("updated_at")
    else:
        warehouse_meta["first_populated_at"] = warehouse_meta["updated_at"]

    paths["reviews"].write_text(json.dumps(merged_rows, indent=2), encoding="utf-8")
    paths["metadata"].write_text(json.dumps(warehouse_meta, indent=2), encoding="utf-8")

    run_result.normalized_reviews = merged_reviews
    run_result.metadata["ingestion_mode"] = "incremental"
    run_result.metadata["incremental_fetch_weeks"] = run_result.metadata["reporting_window"]["lookback_weeks"]
    run_result.metadata["reporting_window"] = {
        "start_date": window_start.isoformat(),
        "end_date": window_end.isoformat(),
        "lookback_weeks": rolling_window_weeks,
    }
    run_result.metadata["warehouse"] = {
        **warehouse_meta["counts"],
        "warehouse_path": str(paths["reviews"]),
    }
    run_result.metadata["assumptions"]["rolling_warehouse"] = (
        f"Incremental weekly fetch merged into a {rolling_window_weeks}-week rolling store."
    )

    if run_result.output_paths:
        run_dir = Path(run_result.output_paths["run_directory"])
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "normalized_reviews.json").write_text(
            json.dumps(merged_rows, indent=2),
            encoding="utf-8",
        )
        (run_dir / "run_metadata.json").write_text(
            json.dumps(run_result.metadata, indent=2),
            encoding="utf-8",
        )
        run_result.output_paths["warehouse_reviews"] = str(paths["reviews"])
        run_result.output_paths["warehouse_metadata"] = str(paths["metadata"])

    return run_result


def bootstrap_warehouse_from_run(
    *,
    run_result: PipelineRunResult,
    run_date: date,
    warehouse_dir: Path,
    rolling_window_weeks: int = DEFAULT_ROLLING_WINDOW_WEEKS,
) -> PipelineRunResult:
    """Replace the warehouse with the current run's normalized reviews (full backfill)."""
    paths = warehouse_paths(warehouse_dir)
    paths["root"].mkdir(parents=True, exist_ok=True)

    window_end = run_date
    window_start = window_end - timedelta(weeks=rolling_window_weeks)
    rows = [
        review.to_dict()
        for review in run_result.normalized_reviews
        if window_start <= review.review_date <= window_end
    ]
    rows.sort(key=lambda row: (row["review_date"], row["source"], row["review_id_hash"]))

    warehouse_meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "first_populated_at": datetime.now(timezone.utc).isoformat(),
        "rolling_window_weeks": rolling_window_weeks,
        "bootstrap": True,
        "reporting_window": {
            "start_date": window_start.isoformat(),
            "end_date": window_end.isoformat(),
            "lookback_weeks": rolling_window_weeks,
        },
        "counts": {"total_reviews": len(rows), "new_reviews_this_run": len(rows), "pruned_outside_window": 0},
        "last_run_id": run_result.metadata.get("run_id"),
    }
    paths["reviews"].write_text(json.dumps(rows, indent=2), encoding="utf-8")
    paths["metadata"].write_text(json.dumps(warehouse_meta, indent=2), encoding="utf-8")

    run_result.metadata["ingestion_mode"] = "bootstrap"
    run_result.metadata["warehouse"] = warehouse_meta["counts"]
    if run_result.output_paths:
        run_dir = Path(run_result.output_paths["run_directory"])
        (run_dir / "normalized_reviews.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        (run_dir / "run_metadata.json").write_text(json.dumps(run_result.metadata, indent=2), encoding="utf-8")
    return run_result
