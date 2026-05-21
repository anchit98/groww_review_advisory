# Deployment Plan — Groww Review Advisory

**Target architecture:** GitHub (source of truth) → **Vercel** (React SPA) + **Render** (FastAPI read API).  
**Pipeline data:** GitHub Actions commits `data/history/` after each weekly run; Render serves that data on deploy.

```text
┌─────────────────────────────────────────────────────────────────┐
│  GitHub repository (main branch)                                 │
│  • Application code (frontend/, backend/, phases/)               │
│  • data/history/ + runs_index.json (updated by weekly workflow)  │
└───────────────┬─────────────────────────────┬───────────────────┘
                │ push                         │ push
                ▼                              ▼
     ┌──────────────────┐           ┌──────────────────────┐
     │  Vercel            │           │  Render Web Service   │
     │  frontend/         │  HTTPS    │  backend/ (FastAPI)   │
     │  VITE_API_URL ─────┼──────────►│  reads data/history/  │
     └──────────────────┘           └──────────────────────┘
                │
                ▼
           End users (browser)
```

**Auth:** None in v1 (public dashboard).  
**Secrets:** Never put `GROQ_API_KEY`, MCP tokens, or `.env` in Vercel or Render for this UI API.

---

## 1. Prerequisites

| Item | Notes |
|------|--------|
| GitHub repo | Push full monorepo; ensure `data/history/runs_index.json` is tracked (not gitignored). |
| Vercel account | Connect to GitHub. |
| Render account | Connect to GitHub. |
| Domain (optional) | Custom domains on Vercel / Render later. |

**Local verification before deploy:**

```bash
# Backend
pip install -r backend/requirements.txt
set REVIEW_ADVISORY_REPO_ROOT=<repo-root>   # PowerShell: $env:REVIEW_ADVISORY_REPO_ROOT="..."
uvicorn review_advisory_api.main:app --reload --app-dir backend
# GET http://127.0.0.1:8000/health

# Frontend
cd frontend && npm install && npm run dev
# Set VITE_API_URL=http://127.0.0.1:8000 in frontend/.env.local
```

---

## 2. Recommended deployment order

1. Push code to GitHub (`main`).
2. Deploy **Render backend** first → copy service URL.
3. Deploy **Vercel frontend** with `VITE_API_URL` pointing at Render.
4. Update Render `CORS_ORIGINS` with the live Vercel URL(s).
5. Redeploy Render if CORS was placeholder during step 2.
6. Run verification checklist (§7).

---

## 3. GitHub repository setup

### 3.1 Initial push

```bash
git init   # if not already a repo
git remote add origin https://github.com/<org>/<repo>.git
git add .
git commit -m "Initial commit: review advisory pipeline and UI"
git push -u origin main
```

### 3.2 What must be in the repo for production UI

| Path | Purpose |
|------|---------|
| `data/history/runs_index.json` | Run list for API |
| `data/history/weekly_pulse/<date>/` | `weekly_pulse.json`, `quote_candidates.json`, metadata |
| `data/store_ratings.json` | Optional; API can refresh live Play/App listing ratings |
| `backend/` | FastAPI service |
| `frontend/` | Vite SPA |

The weekly workflow (`.github/workflows/weekly-review-advisory.yml`) already:

- Runs `scripts/ci/sync_runs_index.py` after a successful pipeline.
- Commits `data/warehouse` and `data/history` back to `main`.

**After the first successful weekly run**, production data stays fresh via git push → Render auto-deploy (if enabled).

### 3.3 GitHub Actions secrets (pipeline only — not Vercel/Render UI)

Configure under **Settings → Secrets and variables → Actions**:

| Secret | Used by |
|--------|---------|
| `GROQ_API_KEY` | Phase 2 live runs |
| `GOOGLE_DOC_ID` | Phase 3 Doc append |
| `GMAIL_DRAFT_TO` | Phase 3 Gmail draft |
| `MCP_SERVER_URL` (optional) | Phase 3 MCP |

These stay in GitHub Actions only. The public UI backend does not need them.

### 3.4 Branch strategy

| Branch | Vercel | Render |
|--------|--------|--------|
| `main` | Production | Production (recommended) |
| PR branches | Preview deployments (optional) | Optional preview service |

If using Vercel previews, add each preview origin to Render `CORS_ORIGINS` (comma-separated).

---

## 4. Render — backend (FastAPI)

### 4.1 Create service

1. [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**.
2. Connect the GitHub repository.
3. Configure:

| Setting | Value |
|---------|--------|
| **Name** | `groww-review-advisory-api` (example) |
| **Region** | Closest to users (e.g. Singapore / Frankfurt) |
| **Branch** | `main` |
| **Root Directory** | *(leave empty — repo root)* |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `uvicorn review_advisory_api.main:app --host 0.0.0.0 --port $PORT --app-dir backend` |
| **Health Check Path** | `/health` |

> **Why repo root?** The API reads `data/history/` at the repository root. If you set Root Directory to `backend` only, you must set `REVIEW_ADVISORY_REPO_ROOT` to the parent path (see env vars).

### 4.2 Environment variables

| Variable | Required | Example |
|----------|----------|---------|
| `REVIEW_ADVISORY_REPO_ROOT` | Recommended on Render | `/opt/render/project/src` |
| `CORS_ORIGINS` | **Yes** | `https://your-app.vercel.app,https://your-app-*.vercel.app,http://localhost:5173` |
| `REVIEW_ADVISORY_HISTORY_DIR` | Optional | `/opt/render/project/src/data/history` (default: `{REPO_ROOT}/data/history`) |

**CORS notes:**

- Include your **production** Vercel URL exactly (no trailing slash).
- Include `http://localhost:5173` for local dev.
- For Vercel preview URLs, either list them or use a stable production domain only.

`CORS_ORIGINS` is parsed in `backend/review_advisory_api/config.py`.

### 4.3 Instance & scaling

| Tier | Fit |
|------|-----|
| **Free** | Personal use; **cold starts** (~30–60s) after idle. |
| **Starter** | Always-on API for smoother UX. |

No database required — filesystem JSON under `data/history/`.

### 4.4 Auto-deploy

Enable **Auto-Deploy** on push to `main` so each weekly `data/history` commit refreshes production.

### 4.5 Optional: `render.yaml` (Blueprint)

You can add a `render.yaml` at repo root later for reproducible infra; manual dashboard setup above is sufficient for v1.

### 4.6 Post-deploy checks

```text
GET https://<service>.onrender.com/health
     → {"status":"ok"}

GET https://<service>.onrender.com/api/runs
     → {"runs":[...],"updated_at":"..."}

GET https://<service>.onrender.com/api/runs/latest
     → latest run summary
```

---

## 5. Vercel — frontend (Vite + React)

### 5.1 Create project

1. [Vercel Dashboard](https://vercel.com) → **Add New** → **Project** → import GitHub repo.
2. Configure:

| Setting | Value |
|---------|--------|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `dist` (default) |
| **Install Command** | `npm install` |

SPA routing is already defined in `frontend/vercel.json` (rewrite to `index.html`).

### 5.2 Environment variables

| Variable | Environment | Value |
|----------|-------------|--------|
| `VITE_API_URL` | Production | `https://<your-render-service>.onrender.com` |
| `VITE_API_URL` | Preview (optional) | Same Render URL or a staging API |

**No trailing slash** on `VITE_API_URL` (the client strips it).

Set in **Project → Settings → Environment Variables**. Rebuild after changing.

### 5.3 Deploy

- **Production:** merge to `main` → Vercel production deploy.
- **Preview:** open PR → Vercel preview URL (update Render CORS if you test previews).

### 5.4 Custom domain (optional)

Vercel → **Domains** → add domain → update Render `CORS_ORIGINS` with the new origin.

---

## 6. Wiring frontend ↔ backend

```text
Browser loads:  https://<app>.vercel.app
Static JS uses: import.meta.env.VITE_API_URL  →  https://<api>.onrender.com
Fetches:        GET /api/runs/latest, /api/runs/{id}/pulse, /quotes, /store-ratings
```

**CORS:** Browser enforces origin; Render must list the Vercel origin in `CORS_ORIGINS`.  
**Mixed content:** Use `https` on both sides.

---

## 7. Verification checklist

After both services are live:

- [ ] `GET <Render>/health` returns `ok`
- [ ] `GET <Render>/api/runs` lists at least one run
- [ ] Vercel app loads Summary / Themes / Quotes without console CORS errors
- [ ] Reporting period and store ratings appear on Summary (if data present)
- [ ] Week comparison works when two weeks exist in `runs_index.json`
- [ ] Mobile layout acceptable on phone width
- [ ] No secrets in Vercel env (only `VITE_API_URL`)

---

## 8. Ongoing operations

### Weekly data refresh

```text
Monday cron (or manual workflow_dispatch)
  → Phases 1–3 run in GitHub Actions
  → sync_runs_index.py updates data/history/
  → bot commits + pushes to main
  → Render auto-deploy picks up new JSON
  → Vercel unchanged (unless frontend code changed)
```

Manual index sync (local or CI debugging):

```bash
python scripts/ci/sync_runs_index.py \
  --run-date 2026-05-21 \
  --weekly-pulse data/history/weekly_pulse/2026-05-21/weekly_pulse.json \
  --phase2-metadata data/history/weekly_pulse/2026-05-21/phase2_run_metadata.json \
  --phase3-metadata data/history/weekly_pulse/2026-05-21/phase3_run_metadata.json \
  --repo-root .
git add data/history && git commit -m "chore(data): sync runs index" && git push
```

### When to redeploy what

| Change | Redeploy |
|--------|----------|
| `data/history/` only | Render (auto on push) |
| `backend/` | Render |
| `frontend/` | Vercel |
| `CORS_ORIGINS` | Render |
| `VITE_API_URL` | Vercel rebuild |

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| UI “Unable to load data” | Wrong `VITE_API_URL` or API down | Check Render URL; rebuild Vercel |
| CORS error in browser | Missing Vercel origin | Add URL to `CORS_ORIGINS`; redeploy Render |
| Empty runs list | `runs_index.json` missing / not deployed | Commit `data/history`; verify `REVIEW_ADVISORY_REPO_ROOT` |
| 404 on `/api/...` | Wrong API base or cold start | Wait for Render wake-up; hit `/health` first |
| Quotes empty | `quote_candidates.json` missing for run | Re-run sync script; check history folder paths in index |
| Store ratings 404 | No `data/store_ratings.json` | Run Phase 1 fetch or `GET /api/store-ratings?refresh=true` once on Render |

---

## 10. Security & cost summary

**Security**

- Public read-only API (`GET` only).
- No auth in v1 — suitable for personal / internal link sharing only.
- Do not expose Groq or MCP credentials on Render for this service.

**Approximate cost (personal use)**

| Service | Free tier caveat |
|---------|------------------|
| Vercel | Hobby sufficient for SPA |
| Render | Free tier cold starts; Starter ~$7/mo for always-on |
| GitHub Actions | Within free minutes for weekly job |

---

## 11. Quick reference — copy/paste

**Render start command**

```bash
uvicorn review_advisory_api.main:app --host 0.0.0.0 --port $PORT --app-dir backend
```

**Render env (template)**

```env
REVIEW_ADVISORY_REPO_ROOT=/opt/render/project/src
CORS_ORIGINS=https://YOUR_APP.vercel.app,http://localhost:5173
```

**Vercel env (template)**

```env
VITE_API_URL=https://YOUR_SERVICE.onrender.com
```

---

## Related docs

- `docs/phases/phase-5/DEPLOY.md` — short Phase 5 deploy notes
- `docs/phases/phase-5/frontend-plan.md` — hosting decisions (Vercel + Render, no auth)
- `.github/workflows/weekly-review-advisory.yml` — data commit to `main`
- `backend/review_advisory_api/config.py` — `REVIEW_ADVISORY_REPO_ROOT`, `CORS_ORIGINS`
