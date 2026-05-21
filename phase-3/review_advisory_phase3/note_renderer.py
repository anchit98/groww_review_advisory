"""Deterministic weekly note rendering for Google Doc and Gmail (same source text)."""

from __future__ import annotations

from typing import Any


def build_google_doc_url(doc_id: str) -> str:
    """Public edit URL for an existing Google Doc."""
    return f"https://docs.google.com/document/d/{doc_id.strip()}/edit"


def render_weekly_pulse_markdown(
    weekly_pulse: dict[str, Any],
    *,
    title: str,
    reporting_label: str,
) -> str:
    """Render the full weekly note (Markdown) for Google Doc append."""
    lines: list[str] = [
        f"# {title}",
        "",
        f"**Reporting period:** {reporting_label}",
        "",
        "## Opening summary",
        "",
        str(weekly_pulse.get("opening_summary", "")).strip(),
        "",
        "## Top themes",
        "",
    ]
    for theme in weekly_pulse.get("top_themes") or []:
        name = str(theme.get("theme_name", "")).strip()
        summary = str(theme.get("summary", "")).strip()
        tid = theme.get("linked_final_theme_id")
        suffix = f" (`{tid}`)" if tid else ""
        lines.append(f"- **{name}**{suffix}: {summary}")
    lines.extend(["", "## Representative quotes", ""])
    for quote in weekly_pulse.get("user_quotes") or []:
        q = str(quote.get("quote", "")).strip()
        theme = str(quote.get("theme_name", "")).strip()
        rid = str(quote.get("review_id_hash", "")).strip()
        lines.append(f"- *{theme}* (review `{rid[:16]}…`): {q}")
    lines.extend(["", "## Action ideas", ""])
    for action in weekly_pulse.get("action_ideas") or []:
        a = str(action.get("action", "")).strip()
        lt = str(action.get("linked_theme", "")).strip()
        lines.append(f"- **{lt}:** {a}")
    note = str(weekly_pulse.get("coverage_note", "")).strip()
    if note:
        lines.extend(["", "## Coverage / caveats", "", note, ""])
    return "\n".join(lines).strip() + "\n"


def build_email_subject(*, reporting_label: str, prefix: str = "Groww review pulse") -> str:
    return f"{prefix}: {reporting_label}"


def render_email_teaser(
    weekly_pulse: dict[str, Any],
    *,
    reporting_label: str,
    google_doc_url: str,
) -> str:
    """Short Gmail draft body with themes, actions, and a link to the full Google Doc."""
    lines: list[str] = [
        f"Weekly Groww review advisory ({reporting_label}).",
        "",
        str(weekly_pulse.get("opening_summary", "")).strip(),
        "",
        "Top themes:",
    ]
    for theme in weekly_pulse.get("top_themes") or []:
        name = str(theme.get("theme_name", "")).strip()
        if name:
            lines.append(f"- {name}")
    lines.extend(["", "Suggested actions:"])
    for action in weekly_pulse.get("action_ideas") or []:
        text = str(action.get("action", "")).strip()
        if text:
            lines.append(f"- {text}")
    note = str(weekly_pulse.get("coverage_note", "")).strip()
    if note:
        lines.extend(["", f"Coverage note: {note}"])
    lines.extend(
        [
            "",
            "Full weekly note (quotes, review IDs, and detail):",
            google_doc_url,
        ]
    )
    return "\n".join(lines).strip() + "\n"
