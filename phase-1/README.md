# Phase 1 Foundations and Review Ingestion

This folder contains the standalone Phase 1 implementation for the Review Advisory Agent. It focuses only on the trusted input layer described in `docs/implementationplan.md` and `docs/architecture.md`.

Phase 1 covers:

- fetching and storing real Groww App Store and Play Store reviews from public store-accessible sources
- loading stored App Store and Play Store review files
- validating minimum required fields
- normalizing both sources into one canonical review schema
- filtering reviews to the reporting window
- retaining only English-language reviews in the normalized dataset
- stripping emojis from retained titles and review text
- excluding reviews with 6 words or fewer
- applying privacy sanitization before downstream use
- deduplicating repeated reviews
- writing normalized outputs and run metadata

Phase 1 does not perform theme generation, summary drafting, Google Docs publication, or Gmail draft creation.

## Folder Structure

- `review_advisory_phase1/` contains the ingestion pipeline package
- `data/raw/<run-date>/` stores dated raw review snapshots fetched for Groww
- `tests/` contains focused Phase 1 tests
- `canonical-schema.json` defines the normalized review output shape

## Accepted Inputs

Phase 1 expects CSV files fetched from approved public store-accessible sources for Groww.

### App Store CSV

Required columns:

- `rating` or `stars`
- `review` or `review_text` or `body` or `content`
- `date` or `review_date` or `created_at` or `updated_at`

Optional columns:

- `title` or `headline`
- `language` or `locale`
- `review_id` or `id`

### Play Store CSV

Required columns:

- `score` or `rating` or `stars`
- `content` or `review` or `review_text` or `body`
- `at` or `date` or `review_date`

Optional columns:

- `title` or `headline`
- `language` or `review_language` or `locale`
- `reviewId` or `review_id` or `id`

## Assumptions

- the reporting window is controlled by the run date and lookback period
- Phase 1 defaults to an 8-week lookback window
- ratings must normalize to integers from 1 to 5
- titles are optional, but review text and review date are required
- only English-language reviews are retained after normalization
- reviews must contain at least 7 words after normalization to remain in the working dataset
- emojis are removed from retained normalized text
- emails, phone-like numbers, URLs, and long numeric identifiers are sanitized before output
- if too few valid reviews remain, the run is marked low-confidence
- App Store public coverage may be shallower than the full requested window because the public RSS feed is pagination-limited

## Outputs

### Raw fetched source files

Each fetch run writes a dated raw snapshot under `data/raw/<run-date>/`:

- `groww_app_store_reviews.csv`
- `groww_play_store_reviews.csv`
- `fetch_manifest.json`

The manifest records:

- run date
- lookback weeks
- earliest and latest review dates fetched per source
- warnings such as public-source coverage limitations
- the raw output paths for that run

### Normalized ingestion outputs

Each run writes output into a run-specific subdirectory under the chosen output directory:

- `normalized_reviews.json`
- `run_metadata.json`

The metadata file includes:

- run ID
- status
- reporting window
- input file paths
- source-level counters
- warnings
- source failures
- non-English, short-review, and emoji-removal counters
- total drop and redaction counts
- low-confidence flag

## How to Run

### 1. Fetch and store real Groww reviews

From the `phase-1` folder:

```bash
python -m review_advisory_phase1.fetch_real_reviews \
  --data-dir data \
  --lookback-weeks 8 \
  --run-date 2026-05-11
```

This stores a dated raw snapshot under `data/raw/2026-05-11/`.

### 2. Run Phase 1 ingestion on the stored real reviews

From the `phase-1` folder:

```bash
python -m review_advisory_phase1 \
  --app-store-csv data/raw/2026-05-11/groww_app_store_reviews.csv \
  --play-store-csv data/raw/2026-05-11/groww_play_store_reviews.csv \
  --output-dir output \
  --run-date 2026-05-11 \
  --lookback-weeks 8
```

The command prints run metadata and output paths as JSON and returns a non-zero exit code if no valid reviews remain after processing.

## How Edge Cases Are Handled

The implementation is aligned with `docs/edge-case.md` for Phase 1 concerns:

- missing or drifted source columns fail clearly
- malformed ratings and dates are dropped safely
- ambiguous slash dates are rejected instead of guessed
- duplicate reviews are removed using a stable review hash
- reviews outside the reporting window are excluded
- non-English reviews are removed from the normalized dataset
- reviews with 6 words or fewer are removed from the normalized dataset
- emojis are stripped from retained titles and review text
- risky text is sanitized before it can enter normalized outputs
- runs with no valid reviews fail clearly
- runs with too few valid reviews are marked low-confidence

## Testing

Run the Phase 1 tests from the `phase-1` folder:

```bash
python -m unittest discover -s tests -t .
```
