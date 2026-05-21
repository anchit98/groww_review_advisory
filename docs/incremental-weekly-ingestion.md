# Incremental Weekly Ingestion

## Overview

Each scheduled refresh:

1. Pulls **only the last week's** new public reviews (App Store + Play Store).
2. Normalizes and **merges** them into `data/warehouse/` (deduped by `review_id_hash`).
3. Keeps a **rolling 8-week** corpus for analysis.
4. Runs Phase 2 Groq on the **combined** warehouse (not new-only in isolation).
5. Archives `weekly_pulse.json` under `data/history/weekly_pulse/<week-ending>/`.

Themes and action items each week reflect the **current rolling window**, while history files let you compare pulses week over week.

## Modes

| Mode | Fetch lookback | Phase 1 flags | Use case |
|------|----------------|---------------|----------|
| **incremental** (default cron) | 1 week | `--incremental` | Weekly operations |
| **bootstrap** | 8 weeks | `--bootstrap-warehouse --lookback-weeks 8` | First-time seed |
| **skip_fetch** | — | `--incremental` | Re-ingest existing raw CSVs |

## Local example

```bash
# Weekly incremental (from phase-1/)
python -m review_advisory_phase1.fetch_real_reviews --data-dir data --lookback-weeks 1 --run-date 2026-05-18
python -m review_advisory_phase1 \
  --app-store-csv data/raw/2026-05-18/groww_app_store_reviews.csv \
  --play-store-csv data/raw/2026-05-18/groww_play_store_reviews.csv \
  --run-date 2026-05-18 \
  --incremental \
  --warehouse-dir ../data/warehouse

# One-time bootstrap
python -m review_advisory_phase1.fetch_real_reviews --data-dir data --lookback-weeks 8 --run-date 2026-05-11
python -m review_advisory_phase1 ... --bootstrap-warehouse --lookback-weeks 8 --warehouse-dir ../data/warehouse
```

## What is *not* incremental today

- **Groq analysis** still runs on the merged rolling set (up to the 1,000-review working-set cap). It does not yet do "diff-only themes on new reviews only."
- **Google Doc** remains append-only; re-runs can duplicate sections unless you use `--skip-publish-if-unchanged`.

## Persistence

- **Local:** `data/warehouse/` and `data/history/` on disk.
- **GitHub Actions:** commits both directories after a successful run (requires `contents: write`).

## Filling a gap (e.g. last pull May 10, today May 21)

When scheduled runs were missed:

1. **Seed** the warehouse from the last good Phase 1 run:
   ```bash
   python scripts/seed_warehouse_from_phase1.py --phase1-run-dir phase-1/output/phase1-2026-05-11-f0813bdc
   ```
2. **Fetch** with enough lookback to cover the gap (example: 2 weeks):
   ```bash
   cd phase-1
   python -m review_advisory_phase1.fetch_real_reviews --data-dir data --lookback-weeks 2 --run-date 2026-05-21
   ```
3. **Merge** with explicit lookback matching the fetch window:
   ```bash
   python -m review_advisory_phase1 \
     --play-store-csv data/raw/2026-05-21/groww_play_store_reviews.csv \
     --run-date 2026-05-21 \
     --lookback-weeks 2 \
     --incremental \
     --warehouse-dir ../data/warehouse
   ```
4. Run Phase 2 / 3 on `data/warehouse/normalized_reviews.json` (via latest `phase-1/output/phase1-…/normalized_reviews.json`).

If App Store RSS returns zero entries, Play Store gap-fill still applies; retry App Store later or add `--app-store-csv` from an older raw snapshot.
