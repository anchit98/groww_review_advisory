# Phase 5 — Frontend & Operator Experience

Phase 5 adds a **web frontend** so internal stakeholders and operators can view weekly review advisories, inspect run health, and (optionally) trigger workflows—without reading raw JSON or digging through GitHub Actions alone.

## Status

**Implemented** — React SPA (`frontend/`) + FastAPI read API (`backend/`). Deploy: **Vercel** (frontend) + **Render** (API). **No auth.**

| Component | Path |
|-----------|------|
| Frontend | `frontend/` |
| API | `backend/review_advisory_api/` |
| Runs index sync | `scripts/ci/sync_runs_index.py` |
| Deploy guide | `DEPLOY.md` |

## Design references (repo)

```
frontend references/stitch_groww_advisory_dashboard/
  executive_precision_dark/DESIGN.md          # tokens, typography, components
  groww_review_advisory_summary_dark_mode/    # Executive Summary screen
  groww_review_advisory_themes_detail/        # Top Themes screen
  groww_review_advisory_quotes_detail/        # Representative Quotes screen
```

Mapping to routes and JSON fields: **`design-reference.md`**.

## When to start

- **Minimum:** Phase 2 produces stable `weekly_pulse.json` (available).
- **Recommended:** Phase 3 publish path proven; Phase 4 GitHub Actions observable.
- **Ideal:** `runs_index.json` published after each weekly workflow run.

## Documents

| File | Purpose |
|------|---------|
| `frontend-plan.md` | Phase plan, architecture, workstreams |
| `design-reference.md` | Screen → route → data mapping, design tokens |
| `eval.md` | Exit criteria and test scenarios |

## Related

- `docs/implementationplan.md` — Phase 5 section
- `docs/architecture.md` — Presentation layer (§10)
- `docs/decision.md` — Decision 015 (accepted)
