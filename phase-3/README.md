# Phase 3 — Google Docs & Gmail (MCP HTTP)

Phase 3 publishes the Phase 2 `weekly_pulse.json` to **Google Docs** (append) and **Gmail** (draft only) through the hosted MCP server. This repo does **not** use the Google client libraries or direct Google REST APIs—only HTTP calls to your MCP deployment.

## MCP server

Default base URL: `https://gmail-docs-mcp.onrender.com`

OpenAPI: `https://gmail-docs-mcp.onrender.com/openapi.json`

Tools used:

| HTTP | Purpose |
|------|---------|
| `POST /append_to_doc` | Append Markdown body to an existing Google Doc (`doc_id` + `content`) |
| `POST /create_email_draft` | Create a Gmail draft (`to`, `subject`, `body`) — **does not send** |

List tools: `GET https://gmail-docs-mcp.onrender.com/tools`

## Configuration (`.env` or environment)

| Variable | Meaning |
|----------|---------|
| `MCP_SERVER_URL` | Base URL (default: URL above) |
| `GOOGLE_DOC_ID` | Target document ID (**append** only; create an empty Doc first in Drive) |
| `GMAIL_DRAFT_TO` | Recipient email for the draft |

## Run

From `phase-3/`:

**Dry run** (renders `weekly_note.md` + `intended_mcp_requests.json`, no network publish):

```bash
python -m review_advisory_phase3 ^
  --weekly-pulse ..\phase-2\output\phase2-2026-05-11-4dd213fe\weekly_pulse.json ^
  --phase2-metadata ..\phase-2\output\phase2-2026-05-11-4dd213fe\run_metadata.json ^
  --output-dir output ^
  --dry-run
```

**Live publish** (requires `GOOGLE_DOC_ID` and `GMAIL_DRAFT_TO`):

```bash
python -m review_advisory_phase3 ^
  --weekly-pulse ..\phase-2\output\phase2-2026-05-11-4dd213fe\weekly_pulse.json ^
  --phase2-metadata ..\phase-2\output\phase2-2026-05-11-4dd213fe\run_metadata.json ^
  --output-dir output
```

Optional flags:

- `--mcp-base-url <url>` — override server URL
- `--google-doc-id` / `--gmail-draft-to` — override env for one run
- `--skip-publish-if-unchanged` — skip MCP calls if rendered body hash matches the last successful run under `--output-dir`

## Behavior (architecture / edge cases)

- **Google Doc** gets the full weekly note (Markdown). **Gmail draft** gets a short teaser (summary, theme/action bullets, link to the Doc).
- **Validation**: required pulse fields, substantive text ~250 word budget (opening + themes + quotes + actions; fails fast if over), simple PII patterns (email/phone-like) on rendered body.
- **Partial success**: if the Doc append succeeds and Gmail draft fails, run metadata records `partial_success` and the pipeline raises with a clear message (§37).
- **Idempotency**: optional content-hash skip; otherwise repeated runs append again—operators should use a dedicated doc per product/stream or rely on `--skip-publish-if-unchanged`.

## Tests

```bash
cd phase-3
python -m unittest
```
