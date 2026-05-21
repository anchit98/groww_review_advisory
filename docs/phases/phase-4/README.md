# Phase 4 — GitHub Actions Operations

Phase 4 makes the Review Advisory Agent runnable every week via **GitHub Actions**, with manual re-run and recovery paths aligned to `docs/edge-case.md`.

## Workflow

- **File:** `.github/workflows/weekly-review-advisory.yml`
- **CI dependencies:** `requirements-ci.txt` (repo root)
- **Helpers:** `scripts/ci/check_phase_result.py`, `scripts/ci/workflow_summary.py`
- **Schedule:** Mondays 06:00 UTC
- **Manual:** Actions → *Weekly Review Advisory* → *Run workflow*
- **Concurrency:** `weekly-review-advisory` group, `cancel-in-progress: false` (queued overlaps)

## Pipeline order

1. **Phase 1** — fetch Groww reviews (optional skip) → normalize (`phase-1/output/…`)
2. **Phase 2** — Groq theme analysis → `weekly_pulse.json` (`phase-2/output/…`)
3. **Phase 3** — append Google Doc + create Gmail draft via MCP HTTP server

## Run modes (manual)

| Mode | Description |
|------|-------------|
| `full` | Fetch + Phase 1 + 2 + 3 (default; used by cron) |
| `skip_fetch` | Reuse `data/raw/<run_date>/` CSVs, then Phase 1–3 |
| `phase3_only` | Publish only; requires `phase2_run_directory` input |

## Required GitHub secrets

| Secret | Purpose |
|--------|---------|
| `GROQ_API_KEY` | Phase 2 live Groq calls |
| `GOOGLE_DOC_ID` | Target Google Doc for append |
| `GMAIL_DRAFT_TO` | Gmail draft recipient |
| `MCP_SERVER_URL` | Optional; defaults to `https://gmail-docs-mcp.onrender.com` |

Do not commit secrets. Configure under **Settings → Secrets and variables → Actions**.

## Artifacts

Each run uploads **`weekly-pulse-<run_id>`** (30-day retention), even on failure:

- `phase-1/data/raw/` and `phase-1/output/`
- `phase-2/output/`
- `phase-3/output/`

## Operator guide

Full procedures: **`OPERATOR_RUNBOOK.md`**

## Evaluation

See `docs/phases/phase-4/eval.md` for exit criteria and test scenarios.

## Related docs

- `docs/implementationplan.md` — Phase 4 scope and checkpoints
- `docs/architecture.md` — Orchestration layer
- `docs/decision.md` — Decision 014 (GitHub Actions)
- `docs/edge-case.md` — Phase 4 / GitHub Actions edge cases (§46A–46C)
