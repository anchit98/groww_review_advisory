from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import history_dir, repo_root
from .listing_ratings import load_listing_ratings

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


class StoreError(RuntimeError):
    pass


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise StoreError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    for base in (repo_root(), history_dir().parent.parent):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    return None


def load_runs_index() -> dict[str, Any]:
    index_path = history_dir() / "runs_index.json"
    if not index_path.exists():
        return {"runs": [], "updated_at": None}
    payload = _load_json(index_path)
    if not isinstance(payload, dict):
        raise StoreError("runs_index.json must be an object.")
    payload.setdefault("runs", [])
    return payload


def find_run_entry(run_id: str) -> dict[str, Any]:
    index = load_runs_index()
    for entry in index.get("runs", []):
        if entry.get("week_ending") == run_id:
            return entry
        if entry.get("phase2_run_id") == run_id:
            return entry
        if entry.get("phase3_run_id") == run_id:
            return entry
    raise StoreError(f"Run not found: {run_id}")


def resolve_quote_candidates_path(entry: dict[str, Any]) -> Path | None:
    raw_indexed = entry.get("quote_candidates_path")
    if raw_indexed:
        resolved = _resolve_path(raw_indexed)
        if resolved:
            return resolved

    meta_path = _resolve_path(entry.get("phase2_run_metadata_path"))
    if meta_path:
        sibling = meta_path.parent / "quote_candidates.json"
        if sibling.exists():
            return sibling

    phase2_run_id = entry.get("phase2_run_id")
    if not phase2_run_id:
        try:
            phase2_meta = load_phase2_metadata(entry)
            phase2_run_id = phase2_meta.get("run_id")
        except StoreError:
            phase2_run_id = None

    if phase2_run_id:
        output_path = repo_root() / "phase-2" / "output" / phase2_run_id / "quote_candidates.json"
        if output_path.exists():
            return output_path
    return None


def load_quote_candidates(entry: dict[str, Any], *, per_theme_limit: int = 5) -> list[dict[str, Any]]:
    path = resolve_quote_candidates_path(entry)
    if path is None:
        raise StoreError("quote_candidates.json not available for this run.")

    payload = _load_json(path)
    if not isinstance(payload, list):
        raise StoreError("quote_candidates.json must be an array.")

    sanitized: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        quote_text = str(row.get("quote_text", "")).strip()
        if not quote_text:
            continue
        sanitized.append(
            {
                "quote_candidate_id": row.get("quote_candidate_id"),
                "review_id_hash": row.get("review_id_hash"),
                "theme_id": row.get("theme_id"),
                "theme_name": row.get("theme_name"),
                "source": row.get("source"),
                "rating": row.get("rating"),
                "review_date": row.get("review_date"),
                "quote_text": sanitize_text(quote_text),
            }
        )

    if per_theme_limit <= 0:
        return sanitized

    by_theme: dict[str, list[dict[str, Any]]] = {}
    theme_order: list[str] = []
    for row in sanitized:
        theme_name = str(row.get("theme_name", ""))
        if theme_name not in by_theme:
            by_theme[theme_name] = []
            theme_order.append(theme_name)
        if len(by_theme[theme_name]) < per_theme_limit:
            by_theme[theme_name].append(row)

    ordered: list[dict[str, Any]] = []
    for theme_name in theme_order:
        ordered.extend(by_theme[theme_name])
    return ordered


def resolve_consolidation_response_path(entry: dict[str, Any]) -> Path | None:
    raw_indexed = entry.get("consolidation_response_path")
    if raw_indexed:
        resolved = _resolve_path(raw_indexed)
        if resolved:
            return resolved

    meta_path = _resolve_path(entry.get("phase2_run_metadata_path"))
    if meta_path:
        sibling = meta_path.parent / "consolidation_response.json"
        if sibling.exists():
            return sibling

    phase2_run_id = entry.get("phase2_run_id")
    if not phase2_run_id:
        try:
            phase2_meta = load_phase2_metadata(entry)
            phase2_run_id = phase2_meta.get("run_id")
        except StoreError:
            phase2_run_id = None

    if phase2_run_id:
        output_path = repo_root() / "phase-2" / "output" / phase2_run_id / "consolidation_response.json"
        if output_path.exists():
            return output_path
    return None


def load_consolidation_response(entry: dict[str, Any]) -> dict[str, Any] | None:
    path = resolve_consolidation_response_path(entry)
    if path is None:
        return None
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return None
    return payload


def enrich_pulse_with_theme_issue_counts(
    pulse: dict[str, Any], entry: dict[str, Any]
) -> dict[str, Any]:
    consolidation = load_consolidation_response(entry)
    if not consolidation:
        return pulse

    final_by_id = {
        theme.get("final_theme_id"): theme
        for theme in consolidation.get("final_themes", [])
        if isinstance(theme, dict) and theme.get("final_theme_id")
    }

    enriched = dict(pulse)
    counts: list[dict[str, Any]] = []
    for theme in enriched.get("top_themes") or []:
        if not isinstance(theme, dict):
            continue
        theme_id = theme.get("linked_final_theme_id")
        final = final_by_id.get(theme_id) if theme_id else None
        review_ids = final.get("supporting_review_ids", []) if final else []
        issue_count = len(review_ids) if isinstance(review_ids, list) else 0
        counts.append(
            {
                "theme_name": theme.get("theme_name"),
                "linked_final_theme_id": theme_id,
                "issue_count": issue_count,
            }
        )

    enriched["theme_issue_counts"] = counts
    return enriched


def load_weekly_pulse(entry: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_path(entry.get("weekly_pulse_path"))
    if path is None:
        raise StoreError("weekly_pulse.json not available for this run.")
    pulse = _load_json(path)
    if not isinstance(pulse, dict):
        raise StoreError("weekly_pulse.json must be an object.")
    pulse = sanitize_pulse(pulse)
    return enrich_pulse_with_theme_issue_counts(pulse, entry)


def load_phase2_metadata(entry: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_path(entry.get("phase2_run_metadata_path"))
    if path is None:
        raise StoreError("phase2 run_metadata.json not available for this run.")
    meta = _load_json(path)
    if not isinstance(meta, dict):
        raise StoreError("phase2 metadata must be an object.")
    return meta


def load_phase3_metadata(entry: dict[str, Any]) -> dict[str, Any] | None:
    path = _resolve_path(entry.get("phase3_run_metadata_path"))
    if path is None:
        return None
    meta = _load_json(path)
    return meta if isinstance(meta, dict) else None


def load_phase1_metadata(phase2_meta: dict[str, Any]) -> dict[str, Any] | None:
    handoff = phase2_meta.get("phase1_handoff") or {}
    raw = handoff.get("phase1_metadata_path") or (phase2_meta.get("input_paths") or {}).get(
        "phase1_metadata"
    )
    path = _resolve_path(raw)
    if path is None:
        return None
    meta = _load_json(path)
    return meta if isinstance(meta, dict) else None


def sanitize_text(value: str) -> str:
    if EMAIL_PATTERN.search(value) or PHONE_PATTERN.search(value):
        return "[Content withheld — possible PII detected]"
    return value


def sanitize_pulse(pulse: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(pulse)
    if cleaned.get("opening_summary"):
        cleaned["opening_summary"] = sanitize_text(str(cleaned["opening_summary"]))
    if cleaned.get("coverage_note"):
        cleaned["coverage_note"] = sanitize_text(str(cleaned["coverage_note"]))
    quotes = []
    for quote in cleaned.get("user_quotes") or []:
        if not isinstance(quote, dict):
            continue
        row = dict(quote)
        if row.get("quote"):
            row["quote"] = sanitize_text(str(row["quote"]))
        quotes.append(row)
    cleaned["user_quotes"] = quotes
    return cleaned


def format_reporting_label(window: dict[str, Any] | None) -> str:
    if not window:
        return "Reporting period unavailable"
    start = window.get("start_date", "")
    end = window.get("end_date", "")
    if not start or not end:
        return "Reporting period unavailable"
    return f"{start} to {end}"


def build_run_summary(entry: dict[str, Any]) -> dict[str, Any]:
    phase2_meta: dict[str, Any] | None = None
    try:
        phase2_meta = load_phase2_metadata(entry)
    except StoreError:
        phase2_meta = None

    phase3_meta = load_phase3_metadata(entry)
    phase1_meta = load_phase1_metadata(phase2_meta) if phase2_meta else None

    reporting_window = entry.get("reporting_window") or (
        phase2_meta.get("reporting_window") if phase2_meta else None
    )
    source_mix = phase2_meta.get("source_mix") if phase2_meta else {}

    return {
        "run_id": entry.get("week_ending"),
        "week_ending": entry.get("week_ending"),
        "phase2_run_id": entry.get("phase2_run_id"),
        "phase3_run_id": entry.get("phase3_run_id"),
        "status": entry.get("status") or (phase2_meta or {}).get("status", "unknown"),
        "phase3_status": entry.get("phase3_status")
        or (phase3_meta or {}).get("status"),
        "phase1_status": (phase1_meta or {}).get("status")
        or (phase2_meta or {}).get("phase1_handoff", {}).get("phase1_status"),
        "phase2_status": (phase2_meta or {}).get("status"),
        "archived_at": entry.get("archived_at"),
        "reporting_window": reporting_window,
        "reporting_label": format_reporting_label(reporting_window),
        "source_mix": source_mix,
        "publication": entry.get("publication")
        or _publication_summary(phase3_meta),
        "google_doc_url": entry.get("google_doc_url")
        or (phase3_meta or {}).get("google_doc_url"),
        "has_pulse": _resolve_path(entry.get("weekly_pulse_path")) is not None,
        "store_listing_ratings": load_listing_ratings(refresh_if_missing=True),
    }


def _publication_summary(phase3_meta: dict[str, Any] | None) -> dict[str, str] | None:
    if not phase3_meta:
        return None
    publication = phase3_meta.get("publication") or {}
    doc = (publication.get("google_doc") or {}).get("status")
    mail = (publication.get("gmail_draft") or {}).get("status")
    if not doc and not mail:
        return None
    return {"google_doc": doc or "unknown", "gmail_draft": mail or "unknown"}


def build_run_detail(entry: dict[str, Any]) -> dict[str, Any]:
    summary = build_run_summary(entry)
    phase2_meta = load_phase2_metadata(entry)
    phase3_meta = load_phase3_metadata(entry)
    phase1_meta = load_phase1_metadata(phase2_meta)

    detail: dict[str, Any] = {
        **summary,
        "phase1": _phase1_public(phase1_meta),
        "phase2": _phase2_public(phase2_meta),
        "phase3": _phase3_public(phase3_meta, entry),
        "links": {
            "google_doc": summary.get("google_doc_url"),
            "weekly_note": _relative_link(entry.get("weekly_note_path")),
        },
    }
    return detail


def _relative_link(raw: str | None) -> str | None:
    if not raw:
        return None
    path = _resolve_path(raw)
    if path is None:
        return None
    try:
        return str(path.relative_to(repo_root()))
    except ValueError:
        return str(path)


def _phase1_public(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not meta:
        return None
    return {
        "run_id": meta.get("run_id"),
        "status": meta.get("status"),
        "warnings": meta.get("warnings", []),
        "source_stats": meta.get("source_stats", {}),
        "totals": meta.get("totals", {}),
    }


def _phase2_public(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": meta.get("run_id"),
        "status": meta.get("status"),
        "run_started_at": meta.get("run_started_at"),
        "run_finished_at": meta.get("run_finished_at"),
        "reporting_window": meta.get("reporting_window"),
        "source_mix": meta.get("source_mix", {}),
        "review_counts": meta.get("review_counts", {}),
        "coverage_notes": meta.get("coverage_notes", []),
        "llm_provider": {
            "name": (meta.get("llm_provider") or {}).get("name"),
            "model": (meta.get("llm_provider") or {}).get("model"),
            "dry_run": (meta.get("llm_provider") or {}).get("dry_run"),
        },
        "groq_limits": meta.get("groq_limits", {}),
    }


def _phase3_public(meta: dict[str, Any] | None, entry: dict[str, Any]) -> dict[str, Any] | None:
    if not meta and not entry.get("publication"):
        return None
    publication = (meta or {}).get("publication") or {}
    return {
        "run_id": (meta or {}).get("run_id") or entry.get("phase3_run_id"),
        "status": (meta or {}).get("status") or entry.get("phase3_status"),
        "google_doc_url": (meta or {}).get("google_doc_url") or entry.get("google_doc_url"),
        "publication": entry.get("publication") or {
            "google_doc": (publication.get("google_doc") or {}).get("status"),
            "gmail_draft": (publication.get("gmail_draft") or {}).get("status"),
        },
        "word_budget": (meta or {}).get("word_budget"),
    }
