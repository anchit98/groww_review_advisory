# Phase 5 Evaluation — Frontend & Operator Experience

## Phase Goal

Validate that stakeholders can read the weekly review advisory in a clear web UI, and operators can understand run status and recover from failures—without relying on raw JSON files or GitHub Actions alone.

## Prerequisites

- Phase 2 produces valid `weekly_pulse.json` for at least one representative run.
- Phase 5 planning references incorporated (`frontend references/`, `design-reference.md`, Decision 015).
- Deployment target and auth model (if any) are agreed.

## What Must Be Tested

### Stakeholder experience

- Summary (`/`): overall sentiment, top 3 themes with quote snippets, 3 actionable insights — matches Stitch Executive Summary
- Themes (`/themes`): theme cards with severity chips and summaries
- Quotes (`/quotes`): 3 quote cards with `review_id_hash` and theme labels
- latest weekly pulse renders: opening summary, top 3 themes, 3 quotes, 3 actions
- coverage note and reporting period are visible
- source mix (App Store vs Play Store) is understandable
- no PII (email, phone, username) appears in the UI
- quotes and themes match the underlying `weekly_pulse.json` (spot-check)

### Operator experience

- run history lists multiple weeks (or clearly shows “single run” MVP scope)
- run detail shows Phase 1–3 status fields from metadata
- failed or partial runs are visually distinct (`partial_success`, publish failures)
- links or instructions to GitHub Actions / Google Doc work when metadata provides ids

### Technical quality

- frontend builds and deploys in CI without secrets in client bundle
- API (if used) does not expose `GROQ_API_KEY` or Gmail/Doc secrets to the browser
- responsive layout usable on laptop; mobile read acceptable for pulse page

### Optional (v1.1)

- manual “trigger workflow” from UI completes successfully via backend
- “Phase 3 only” recovery action documented and tested

## Test Scenarios

| ID | Scenario | Expected |
|----|----------|----------|
| F1 | Load home with latest run | Pulse content matches JSON |
| F2 | No runs available | Empty state with guidance |
| F3 | Phase 2 failed run in history | Error badge; no fake pulse |
| F4 | Phase 3 partial success | Doc OK, draft failed — both visible |
| F5 | Long quote text | Readable layout, no overflow break |
| F6 | PII in source quote | Blocked at pipeline; if leaked, UI review fails gate |

## Evidence Required

- screenshots or screen recording of pulse + history + detail
- deployed URL (or staging) for sign-off
- test checklist signed for PII and structure
- if API: OpenAPI or README for endpoints

## Exit Criteria

- [ ] Design references applied; Summary/Themes/Quotes match Stitch mockups at laptop width
- [ ] Weekly pulse structure matches product constraints (3/3/3 themes/quotes/actions)
- [ ] Run metadata accurately reflected for Phases 1–3
- [ ] Security review: no secrets in frontend, no PII displayed
- [ ] Stakeholder sign-off: “readable in a few minutes”
- [ ] Operator sign-off: can diagnose last failed run from UI + linked Actions

## Phase Sign-Off Question

Can internal teams use the frontend as the default way to read the weekly pulse and understand operational status, while the batch pipeline remains the source of truth?
