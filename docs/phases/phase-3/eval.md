# Phase 3 Evaluation

## Phase Goal

Validate that the weekly note can be published to Google Docs and prepared as a Gmail draft through MCP servers only.

## What Must Be Tested

- Google Docs MCP integration can create or update the weekly note successfully
- Gmail MCP integration can create a draft with the correct content and recipients
- the workflow does not rely on direct Google APIs
- integration failures are surfaced clearly and can be retried safely
- repeated runs behave predictably and do not create uncontrolled duplicates

## Test Scenarios

### Functional Tests

- create a Google Doc from a generated weekly note through MCP
- create a Gmail draft from the same weekly note through MCP
- verify the document and draft contain the expected content structure
- verify recipient configuration works for a user address or internal alias

### Failure Handling Tests

- simulate MCP permission issues and confirm graceful failure behavior
- simulate temporary MCP server unavailability and confirm retry or operator feedback
- simulate partial success where the document is created but the draft fails, and confirm run status is recorded correctly

### Compliance Tests

- confirm there is no direct API client path in the integration flow
- confirm PII is not introduced during document or email generation
- confirm the first release only drafts emails and does not auto-send them

### Idempotency Tests

- re-run a successful publish flow and confirm duplicate handling follows the expected rule
- verify repeated failures do not create inconsistent state without clear logs

## Evidence Required

- successful Google Docs MCP run evidence
- successful Gmail MCP run evidence
- failure case logs
- operator notes for retry and recovery behavior

## Exit Criteria

- Google Docs publication works through MCP in a representative environment
- Gmail draft creation works through MCP in a representative environment
- failure states are understandable and recoverable
- no direct API integration path exists in the shipped implementation
- document and email content match the approved weekly note output

## Phase Sign-Off Question

Can the agent reliably publish its results through MCP-based Google Docs and Gmail integrations without bypassing the intended integration model?
