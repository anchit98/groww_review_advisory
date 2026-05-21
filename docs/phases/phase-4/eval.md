# Phase 4 Evaluation

## Phase Goal

Validate that the system is operationally ready for recurring weekly use with **GitHub Actions** orchestration, clear observability, predictable stage sequencing, and safe recovery behavior.

## What Must Be Tested

- the end-to-end workflow runs successfully from ingestion to draft creation inside GitHub Actions
- **weekly `schedule`** and **`workflow_dispatch`** triggers behave as expected
- required secrets are loaded from GitHub (not hard-coded in the repo)
- workflow **artifacts** contain phase outputs (`run_metadata.json`, `weekly_pulse.json`, etc.)
- logs and run metadata are sufficient for debugging
- partial failures are visible and recoverable
- operators have enough documentation to run and support the system

## Test Scenarios

### End-to-End Tests

- run the full workflow on `workflow_dispatch` and confirm successful completion
- verify the final outputs include the Google Doc and Gmail draft for the same reporting period
- verify each phase’s `run_metadata.json` records stage-level outcomes
- download workflow artifacts and confirm paths match documented layout

### GitHub Actions Operational Tests

- trigger the workflow manually via **Actions → Run workflow** and confirm success
- confirm the **weekly cron** schedule is documented (day, time, timezone) and fires as expected in a test window or dry-run substitute
- confirm repository **secrets** are present: `GROQ_API_KEY`, `GOOGLE_DOC_ID`, `GMAIL_DRAFT_TO` (and `MCP_SERVER_URL` if overridden)
- confirm failed jobs show a clear failing step (Phase 1, 2, or 3) in the Actions log
- optional: test `workflow_dispatch` input for dry-run / skip-publish when implemented

### Failure Recovery Tests

- fail the run at each major phase and confirm the workflow stops with a non-success status
- verify an operator can re-run via `workflow_dispatch` without corrupting state
- verify partial success (e.g. Doc append OK, Gmail draft failed) is recorded in Phase 3 metadata and visible in logs
- confirm Phase 3-only recovery path is documented when Phases 1–2 artifacts already exist

### Supportability Tests

- use only the runbook and Actions logs/artifacts to diagnose a failed run
- confirm an operator can identify whether the issue came from data, Groq limits, or MCP integration

## Evidence Required

- successful GitHub Actions run URL(s) for end-to-end completion
- sample workflow logs and uploaded artifacts
- operator runbook: `docs/phases/phase-4/OPERATOR_RUNBOOK.md`
- recovery notes from at least one simulated failure scenario (cancelled step, invalid secret, or MCP timeout)

## Exit Criteria

- the full weekly workflow runs successfully end to end in GitHub Actions
- weekly schedule and manual dispatch are both documented and tested
- secrets and artifacts are verified; no credentials committed to the repository
- stage-level failures are logged and understandable from Actions
- the system supports safe retries and repeat weekly operation
- stakeholders can receive a consistent weekly output with manageable operational overhead

## Phase Sign-Off Question

Is the system dependable enough to be used as a recurring weekly process via GitHub Actions by the intended internal team?
