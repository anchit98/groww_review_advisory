from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import cors_origins
from .listing_ratings import fetch_live_listing_ratings, load_listing_ratings
from .store import (
    StoreError,
    build_run_detail,
    build_run_summary,
    find_run_entry,
    load_quote_candidates,
    load_runs_index,
    load_weekly_pulse,
)

app = FastAPI(
    title="Groww Review Advisory API",
    version="1.0.0",
    description="Read-only API for weekly pulse and operator run metadata.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/runs")
def list_runs() -> dict[str, object]:
    index = load_runs_index()
    runs = [build_run_summary(entry) for entry in index.get("runs", [])]
    runs.sort(key=lambda row: row.get("week_ending", ""), reverse=True)
    return {"updated_at": index.get("updated_at"), "runs": runs}


@app.get("/api/store-ratings")
def get_store_ratings(refresh: bool = False) -> dict[str, object]:
    if refresh:
        try:
            payload = fetch_live_listing_ratings()
            from .listing_ratings import listing_ratings_path

            path = listing_ratings_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return payload
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    payload = load_listing_ratings(refresh_if_missing=True)
    if not payload:
        raise HTTPException(status_code=404, detail="Store listing ratings unavailable.")
    return payload


@app.get("/api/runs/latest")
def latest_run() -> dict[str, object]:
    index = load_runs_index()
    runs = index.get("runs", [])
    if not runs:
        raise HTTPException(status_code=404, detail="No runs indexed yet.")
    sorted_runs = sorted(runs, key=lambda row: row.get("week_ending", ""), reverse=True)
    entry = sorted_runs[0]
    return {"run": build_run_summary(entry)}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    try:
        entry = find_run_entry(run_id)
    except StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"run": build_run_detail(entry)}


@app.get("/api/runs/{run_id}/pulse")
def get_run_pulse(run_id: str) -> dict[str, object]:
    try:
        entry = find_run_entry(run_id)
        pulse = load_weekly_pulse(entry)
        summary = build_run_summary(entry)
    except StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": summary["run_id"],
        "reporting_label": summary["reporting_label"],
        "weekly_pulse": pulse,
    }


@app.get("/api/runs/{run_id}/quotes")
def get_run_quotes(run_id: str, per_theme: int = 5) -> dict[str, object]:
    try:
        entry = find_run_entry(run_id)
        quotes = load_quote_candidates(entry, per_theme_limit=max(1, min(per_theme, 10)))
        summary = build_run_summary(entry)
    except StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": summary["run_id"],
        "per_theme_limit": max(1, min(per_theme, 10)),
        "quote_candidates": quotes,
    }


@app.get("/api/runs/{run_id}/metadata")
def get_run_metadata(run_id: str) -> dict[str, object]:
    try:
        entry = find_run_entry(run_id)
        detail = build_run_detail(entry)
    except StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": detail["run_id"],
        "phase1": detail.get("phase1"),
        "phase2": detail.get("phase2"),
        "phase3": detail.get("phase3"),
        "links": detail.get("links"),
    }
