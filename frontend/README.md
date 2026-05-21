# Groww Review Advisory — Frontend (Phase 5)

React 18 + Vite + TypeScript + Tailwind. **Executive Precision Dark** design system.

## Routes

| Path | Screen |
|------|--------|
| `/` | Executive Summary |
| `/themes` | Top Themes (no prevalence / impact widgets) |
| `/quotes` | Representative Quotes |

## Local development

1. Start the API (repo root):

   ```bash
   pip install -r backend/requirements.txt
   uvicorn review_advisory_api.main:app --reload --app-dir backend
   ```

2. Install and run the UI:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Open http://localhost:5173 — Vite proxies `/api` and `/health` to port 8000.

## Production (Vercel)

- Root directory: `frontend`
- Build: `npm run build`
- Output: `dist`
- Env: `VITE_API_URL` = Render FastAPI base URL (no trailing slash)

See `docs/phases/phase-5/DEPLOY.md`.
