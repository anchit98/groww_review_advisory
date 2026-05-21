# Rolling review warehouse

Persistent store of normalized reviews across weekly runs.

| File | Purpose |
|------|---------|
| `normalized_reviews.json` | Merged English reviews (deduped by `review_id_hash`) |
| `warehouse_metadata.json` | Rolling window, counts, last run id |

## Weekly incremental flow

1. **Fetch** only the last **1 week** of raw reviews from App Store + Play Store.
2. **Phase 1** ingests that slice with `--incremental` and merges into this warehouse.
3. Reviews older than **8 weeks** are pruned automatically.
4. **Phase 2** analyzes the full warehouse corpus (still capped at 1,000 for Groq).
5. **`data/history/weekly_pulse/<date>/`** stores each week's pulse JSON for week-over-week comparison.

## First-time setup

Run once with **`bootstrap`** mode (8-week fetch + `--bootstrap-warehouse`) to seed the warehouse from a full backfill. Scheduled runs then use **`incremental`** mode.

## GitHub Actions

Successful weekly runs commit updates under `data/warehouse/` and `data/history/` so the next run continues from stored history.
