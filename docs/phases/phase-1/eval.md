# Phase 1 Evaluation

## Phase Goal

Validate that the system can reliably fetch and ingest real Groww App Store and Play Store reviews from public store-accessible sources, normalize them into a common schema, and remove or mask risky content before analysis.

## What Must Be Tested

- file ingestion works for the approved input formats
- public-source fetching stores a dated raw snapshot for each run
- required fields are mapped correctly into the canonical schema
- invalid or malformed rows are handled safely
- duplicate reviews are detected consistently
- date filtering for the target 8-week window is correct
- only English-language reviews are retained in the normalized dataset
- reviews with 6 words or fewer are excluded from the normalized dataset
- emojis are removed from retained normalized review text
- PII filtering or masking is applied before downstream processing
- ingestion logs record counts, warnings, and failures clearly

## Test Scenarios

### Functional Tests

- ingest a valid App Store export and confirm all rows are loaded
- ingest a valid Play Store export and confirm all rows are loaded
- fetch real Groww reviews from both stores and confirm raw files are stored for the run date
- ingest real source files from both stores and confirm normalization produces one common schema
- run ingestion on data with missing optional fields and verify safe handling

### Negative Tests

- provide malformed files and confirm graceful failure with useful error messages
- provide rows missing required content and confirm they are rejected or flagged
- provide duplicate reviews and confirm deduplication works as intended

### Data Quality Tests

- confirm dates are parsed consistently
- confirm ratings are normalized to the expected range
- confirm review text is preserved without unwanted truncation
- confirm records outside the target time window are excluded
- confirm English-only filtering behaves correctly when source language metadata is present or missing
- confirm short reviews are removed when they do not exceed the minimum word threshold
- confirm emojis are removed from retained normalized reviews
- confirm source coverage limitations are surfaced when a public source cannot reach the full requested window

### Privacy Tests

- use fixture reviews containing email-like text, IDs, or names and verify the filter removes or masks them
- confirm no raw PII reaches downstream prompts or persisted artifacts

## Evidence Required

- raw fetch manifest and stored source files for a real run
- real ingestion run output
- normalized dataset produced from real Groww reviews
- log excerpts for success and failure cases
- test fixture set covering both stores and edge cases

## Exit Criteria

- real Groww reviews are fetched and stored for the run date
- ingestion succeeds for approved App Store and Play Store source files
- canonical schema is stable and documented
- malformed inputs fail safely without breaking the run
- duplicate detection is working for known duplicate cases
- English-only and minimum-word-count filtering behave as specified
- retained normalized reviews do not contain emojis
- PII controls are verified on representative edge cases
- logs are sufficient for an operator to diagnose ingestion issues

## Phase Sign-Off Question

Can the team trust the input data pipeline enough to use it as the foundation for analysis in the next phase?
