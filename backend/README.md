# Groww Review Advisory — API (Phase 5)

Read-only FastAPI service over `data/history/runs_index.json` and archived weekly artifacts.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/api/runs` | Run index (newest first) |
| GET | `/api/runs/latest` | Latest run summary |
| GET | `/api/runs/{run_id}` | Run detail (`week_ending` or phase run id) |
| GET | `/api/runs/{run_id}/pulse` | `weekly_pulse.json` (PII-sanitized) |
| GET | `/api/runs/{run_id}/metadata` | Phase 1–3 public metadata |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `REVIEW_ADVISORY_REPO_ROOT` | repo root | Resolve artifact paths |
| `REVIEW_ADVISORY_HISTORY_DIR` | `{root}/data/history` | `runs_index.json` location |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated SPA origins |

## Local run

```bash
pip install -r backend/requirements.txt
cd backend
uvicorn review_advisory_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests

```bash
pip install -r backend/requirements.txt httpx
cd backend
python -m unittest discover -s tests -q
```

## Render deploy

- Start command: `uvicorn review_advisory_api.main:app --host 0.0.0.0 --port $PORT`
- Root directory: `backend` (or repo root with `cd backend`)
- Mount persistent disk at repo `data/` or sync `data/history` after each weekly workflow
