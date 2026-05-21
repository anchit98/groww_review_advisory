# Phase 4 Operator Runbook — GitHub Actions

This runbook covers recurring operation of the **Weekly Review Advisory** workflow. Edge-case behavior is defined in `docs/edge-case.md` (§42–46C).

## Workflow location

- **File:** `.github/workflows/weekly-review-advisory.yml`
- **Name in Actions UI:** Weekly Review Advisory

## Triggers

| Trigger | When | Default behavior |
|---------|------|------------------|
| **Schedule** | Mondays 06:00 UTC | Full pipeline: fetch → Phase 1 → 2 → 3 |
| **workflow_dispatch** | Manual | Choose run mode and options (see below) |

## Required GitHub secrets

Configure under **Settings → Secrets and variables → Actions**:

| Secret | Required when | Purpose |
|--------|----------------|---------|
| `GROQ_API_KEY` | Live Phase 2 | Groq theme analysis |
| `GOOGLE_DOC_ID` | Live Phase 3 | Google Doc append target |
| `GMAIL_DRAFT_TO` | Live Phase 3 | Gmail draft recipient |
| `MCP_SERVER_URL` | Optional | Defaults to `https://gmail-docs-mcp.onrender.com` |

Never commit secrets to the repository. GitHub masks secret values in logs.

## Manual run modes (`workflow_dispatch`)

| Run mode | Use when |
|----------|----------|
| **incremental** | Default weekly run: fetch **1 week**, merge into `data/warehouse`, analyze rolling 8-week corpus |
| **bootstrap** | First-time (or rebuild): fetch **8 weeks**, replace warehouse |
| **skip_fetch** | Raw CSV for `run_date` already exists; incremental merge + Phases 2–3 |
| **phase3_only** | Phases 1–2 already succeeded; retry MCP publish only |

Scheduled cron uses **incremental** automatically.

### Common manual options

| Input | Effect |
|-------|--------|
| `run_date` | Reporting reference date (UTC). Default: today UTC |
| `phase2_run_directory` | **Required for phase3_only** — e.g. `output/phase2-2026-05-11-4dd213fe` |
| `phase2_dry_run` | Phase 2 prepares prompts only; no Groq calls |
| `dry_run_phase3` | Phase 3 renders note only; no MCP calls |
| `skip_publish_if_unchanged` | Phase 3 skips MCP if note body hash matches last publish |

## Pipeline order

1. **Fetch** (unless `skip_fetch` or `phase3_only`) — `phase-1/data/raw/<run_date>/`
2. **Phase 1** — normalize → `phase-1/output/phase1-<date>-<id>/`
3. **Phase 2** — Groq → `weekly_pulse.json`
4. **Phase 3** — MCP Doc append + Gmail draft

## Concurrency (edge case 46A)

- **Group:** `weekly-review-advisory`
- **cancel-in-progress:** `false` — overlapping runs queue rather than cancel

Avoid starting two full runs for the same week unless testing. Each run gets a distinct phase `run_id` and GitHub `run_id`.

## Artifacts

Every run uploads **`weekly-pulse-<github_run_id>`** (30-day retention), including:

- `phase-1/data/raw/` and `phase-1/output/`
- `phase-2/output/`
- `phase-3/output/`

Artifacts upload **even on failure** (`if: always()`).

## Reading a run

1. Open **Actions** → select the workflow run.
2. Check the **Summary** tab (job summary from `scripts/ci/workflow_summary.py`).
3. Open the failing step (Phase 1, 2, or 3).
4. Download artifacts for `run_metadata.json`, `weekly_pulse.json`, and MCP intended requests.

## Recovery matrix

| Failure | Likely cause | Recovery |
|---------|--------------|----------|
| Fetch / Phase 1 | Network, empty stores, bad CSV | Fix connectivity; re-run **full** or **skip_fetch** if raw exists |
| Phase 2 | Groq 429 / 403, validation | Wait for quota; inspect `phase-2/output/...`; re-run from Phase 2 or full |
| Phase 3 Doc | MCP down, bad `GOOGLE_DOC_ID` | Fix secret/MCP; **phase3_only** with same `phase2_run_directory` |
| Phase 3 Gmail only | `partial_success` in metadata | Doc already appended; fix Gmail/MCP; **phase3_only** retry |
| Phase 3 `invalid_grant` | Expired/revoked Google refresh token on MCP host | **Re-authenticate** the MCP server (see below); moving OAuth to Production alone does not refresh old tokens |
| Duplicate Doc text | Full re-run append | Expected (append-only); use `skip_publish_if_unchanged` or dedicated Doc per stream |

### MCP OAuth re-auth (`invalid_grant`)

Moving the Google Cloud OAuth app from **Testing** to **Production** stops *new* refresh tokens from expiring after 7 days, but the token already stored on Render is still invalid until you sign in again.

1. Run the MCP server’s original OAuth setup (local script or browser flow that writes `token.json` / updates Render env vars).
2. Confirm Render persists credentials (persistent disk or secrets), not only the container filesystem.
3. Smoke-test: `POST /append_to_doc` with a one-line body — response must include `"status": "success"`, not `invalid_grant`.
4. Re-run Phase 3 locally or **phase3_only** in Actions.

### Phase 3-only example

1. Actions → **Run workflow**
2. `run_mode` = **phase3_only**
3. `phase2_run_directory` = `output/phase2-2026-05-11-4dd213fe` (from prior artifact)
4. Leave `dry_run_phase3` false for live publish

## Local fallback

If Actions is blocked, run phases locally from each folder (see phase READMEs). Use the same env vars as GitHub secrets.

## Release readiness checklist

- [ ] Secrets configured in GitHub
- [ ] One successful `workflow_dispatch` **full** run
- [ ] One **phase3_only** recovery drill documented
- [ ] Artifacts inspected for `weekly_pulse.json` and Phase 3 publication metadata
- [ ] Cron schedule confirmed (Mondays 06:00 UTC)

## Related

- `docs/phases/phase-4/eval.md` — exit criteria
- `docs/decision.md` — Decision 014
- `docs/edge-case.md` — §46A–46C
