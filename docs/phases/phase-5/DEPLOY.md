# Phase 5 Deployment

> **Full step-by-step plan:** [`docs/DEPLOYMENT_PLAN.md`](../../DEPLOYMENT_PLAN.md) (GitHub → Render → Vercel, env vars, checklist, ops).

## Architecture

```text
Browser → Vercel (React SPA, VITE_API_URL)
              ↓
         Render (FastAPI, reads data/history/)
```

No authentication in v1. Do not put `GROQ_API_KEY`, MCP secrets, or `.env` in Vercel.

## Backend (Render)

1. Create a **Web Service** from this repository.
2. **Root directory:** `backend` (or set start command from repo root).
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn review_advisory_api.main:app --host 0.0.0.0 --port $PORT`
5. **Environment:**
   - `REVIEW_ADVISORY_REPO_ROOT` = `/opt/render/project/src` (or Render project path)
   - `CORS_ORIGINS` = `https://your-app.vercel.app,http://localhost:5173`
6. **Data:** After each weekly GitHub Actions run, ensure `data/history/` (including `runs_index.json`) is present on the service — via git deploy, persistent disk, or rsync from CI artifact.

Health check path: `/health`

## Frontend (Vercel)

1. Import repo; set **Root Directory** to `frontend`.
2. Framework preset: **Vite**.
3. **Environment variable:** `VITE_API_URL` = `https://<your-render-service>.onrender.com`
4. Deploy. SPA routing uses `frontend/vercel.json`.

## Refresh index after pipeline

GitHub Actions runs `scripts/ci/sync_runs_index.py` after archive (see `weekly-review-advisory.yml`). Locally:

```bash
python scripts/ci/sync_runs_index.py \
  --run-date 2026-05-21 \
  --weekly-pulse data/history/weekly_pulse/2026-05-21/weekly_pulse.json \
  --phase2-metadata data/history/weekly_pulse/2026-05-21/phase2_run_metadata.json \
  --phase3-metadata data/history/weekly_pulse/2026-05-21/phase3_run_metadata.json \
  --repo-root .
```

## Local full stack

```bash
# Terminal 1
pip install -r backend/requirements.txt
uvicorn review_advisory_api.main:app --reload --app-dir backend

# Terminal 2
cd frontend && npm install && npm run dev
```

Open http://localhost:5173
