# Project Decision Log

This file captures the major technical and logical decisions taken while defining and shaping the Review Advisory Agent. It is intentionally limited to high-impact choices that affect architecture, delivery strategy, trust model, operating model, or business behavior.

This is not a backlog of small implementation details. If a choice does not materially influence how the project is designed, delivered, or operated, it does not belong here.

## Decision 001: Use MCP for Google Docs and Gmail

### Status

Accepted

### Context

The workflow must publish the weekly pulse into Google Docs and create a Gmail draft. There are multiple possible integration patterns, including direct Google APIs, custom OAuth clients, or MCP-based tool access.

### Decision

Use MCP servers for both Google Docs and Gmail integrations. Do not implement direct Google API clients in the initial solution.

### Why

- aligns with the product requirement
- standardizes tool access for the AI agent
- reduces custom integration surface area
- keeps the external action layer consistent with agent workflows

### Consequences

- MCP server availability and permissions become release dependencies
- integration testing must validate MCP behavior explicitly
- direct API fallbacks are not part of the initial scope

## Decision 002: Start with a Weekly Batch Workflow

### Status

Accepted

### Context

The business need is a weekly pulse for internal stakeholders, not continuous live monitoring.

### Decision

Implement the first release as a scheduled or manually triggered weekly batch process. Phase 4 specifies **GitHub Actions** as the production scheduler (see Decision 014).

### Why

- matches the reporting cadence in the problem statement
- lowers operational complexity
- makes evaluation easier during the first release

### Consequences

- near-real-time trend visibility is out of scope
- summary freshness is tied to the weekly run cadence

## Decision 003: Use Public Store-Accessible Review Sources Only

### Status

Accepted

### Context

The solution needs real Groww review data but must avoid risky or non-compliant extraction methods.

### Decision

Use only approved public store-accessible review sources as the system input. Do not scrape behind logins, depend on private sources, or use authenticated private APIs.

### Why

- reduces compliance and access risk
- keeps the ingestion layer simpler and more auditable

### Consequences

- coverage depends on the quality and availability of public sources
- ingestion logic must tolerate source format differences
- some public sources may not expose the full requested historical window

## Decision 004: Keep Human Review Before Distribution

### Status

Accepted

### Context

The system will generate summaries and action ideas, but internal stakeholders should retain final control over distribution.

### Decision

Create a Gmail draft for review instead of automatically sending the email in the first release.

### Why

- reduces the risk of distributing low-quality or misleading summaries
- preserves trust while the agent quality matures

### Consequences

- the workflow is not fully autonomous end to end
- operator review becomes part of the weekly process

## Decision 005: Enforce a Tight Summary Format

### Status

Accepted

### Context

The weekly pulse is intended for busy stakeholders who need a fast and scannable summary.

### Decision

Limit the output to the top 3 themes, 3 representative quotes, 3 action ideas, and a target length of 250 words or less.

### Why

- keeps the output easy to review
- forces prioritization of the most important signals
- improves consistency across weekly runs

### Consequences

- lower-priority but still useful issues may be excluded
- summarization quality matters more because the format is compact

## Decision 006: Cap Theme Count at Five

### Status

Accepted

### Context

Too many themes makes the output noisy and reduces actionability.

### Decision

Cluster reviews into no more than 5 themes in the underlying analysis.

### Why

- keeps the model output focused
- makes prioritization easier for stakeholders

### Consequences

- similar but distinct issues may need to be merged
- theme naming and ranking must be handled carefully

## Decision 007: Deliver the Project in Phase Gates

### Status

Accepted

### Context

The project includes multiple layers of uncertainty: source data quality, output quality, MCP integration reliability, and ongoing operational readiness. Attempting to deliver everything at once would make it harder to isolate risk and harder to know when the system is ready to advance.

### Decision

Deliver the project in clearly separated phases, with each phase requiring its own evaluation and exit criteria before the next phase begins.

### Why

- reduces delivery risk by validating one layer at a time
- makes progress easier to assess objectively
- prevents late-stage surprises from weak foundations
- gives the project a clearer governance model

### Consequences

- delivery becomes more structured and gate-driven
- documentation and evaluation effort increases
- some useful end-to-end capabilities arrive later by design

## Decision 008: Phase 1 Must Use Real Groww Reviews, Not Samples

### Status

Accepted

### Context

Sample fixtures are useful for edge-case testing, but they are not enough to validate the real ingestion path for this project. Phase 1 needs to prove that the system can work with actual Groww reviews from both stores.

### Decision

Use real Groww App Store and Play Store reviews in Phase 1, and treat synthetic fixtures as test support only.

### Why

- validates the project against actual source behavior and data quality
- makes Phase 1 evidence meaningful for later phases
- reduces the risk of building around unrealistic sample assumptions

### Consequences

- Phase 1 depends on live public-source availability
- evaluation must include evidence from real fetched review data
- test fixtures remain useful, but they are no longer the primary proof of Phase 1 success

## Decision 009: Store Dated Raw Review Snapshots Per Fetch Run

### Status

Accepted

### Context

The project needs a reliable way to audit what source data was available for a given weekly run, especially when public-source coverage may vary by store and by day.

### Decision

Store raw source files in dated snapshot folders for each fetch run before Phase 1 normalization.

### Why

- preserves auditability for ingestion behavior
- makes reruns and debugging easier
- keeps source coverage limitations visible instead of hidden

### Consequences

- storage grows over time as snapshots accumulate
- operators need to know which dated snapshot was used for a given run
- documentation and run metadata must consistently reference the snapshot path

## Decision 010: Normalize Phase 1 to English-Only, Emoji-Free, Higher-Signal Reviews

### Status

Accepted

### Context

Raw store reviews include low-signal one-line reactions, emojis, and reviews in multiple languages. Leaving all of them in the normalized dataset would make downstream clustering and summarization noisier and less consistent.

### Decision

Retain only English-language reviews in the Phase 1 normalized dataset, strip emojis from retained text, and exclude reviews with 6 words or fewer.

### Why

- improves the signal quality of the working dataset
- reduces downstream noise in theme extraction and quoting
- makes later phases easier to evaluate consistently

### Consequences

- the normalized dataset will be smaller than the raw fetched dataset
- some short but emotionally strong reviews will be intentionally excluded
- language filtering may require heuristic handling when source language metadata is missing

## Decision 011: Use Groq as the Phase 2 LLM Provider

### Status

Accepted

### Context

Phase 2 is the first stage where semantic clustering, theme naming, evidence-backed summarization, and action drafting are introduced. The project needs a clear LLM provider choice before prompt design and evaluation work can be finalized.

### Decision

Use Groq as the LLM provider for Phase 2 review intelligence and weekly note generation.

### Why

- creates a concrete target for prompt and batching design
- lets Phase 2 evaluation focus on one provider behavior rather than abstract LLM assumptions
- supports a deliberate hybrid strategy where deterministic preprocessing happens before the Groq calls

### Consequences

- prompt design, batching, and evaluation will be tuned to Groq behavior
- provider-specific limits and response quality characteristics must be accounted for in Phase 2
- switching providers later would be a meaningful architecture change, not a minor configuration tweak

## Decision 012: Cap the Initial Phase 2 Groq Working Set at 1,000 Reviews

### Status

Accepted

### Context

The current normalized Phase 1 dataset is larger than the preferred live LLM working set, and the chosen Groq model has practical rate and token limits that make unrestricted weekly analysis unnecessarily expensive and noisy.

### Decision

For the initial Phase 2 release, cap the live Groq working set at 1,000 normalized reviews per weekly run.

### Why

- keeps token usage manageable under the Groq model limits
- reduces prompt noise from over-large weekly corpora
- forces deterministic evidence shaping before LLM analysis

### Consequences

- not every normalized review will be sent to Groq in the first release
- selection strategy becomes part of summary quality and must be evaluated carefully
- rare but important issues must be protected by the deterministic prioritization strategy

## Decision 013: Design Phase 2 Around Token Budget First

### Status

Accepted

### Context

For the selected Groq model, token-per-minute is the tighter operational constraint than request-per-minute for multi-step theme discovery and summary generation.

### Decision

Design Phase 2 batching and call sequencing around token budget first, with a conservative live-call plan of roughly 10 Groq calls or fewer per weekly run and safety margin below the provider TPM limit.

### Why

- reflects the actual bottleneck for structured multi-step LLM analysis
- leaves operational headroom for retries and final rendering calls
- reduces the risk of development and production runs hitting provider limits unexpectedly

### Consequences

- batching must be intentionally conservative
- dry runs and cached artifacts become important during prompt iteration
- some larger raw evidence sets must be summarized or reduced before live LLM use

## Decision 014: Use GitHub Actions for Phase 4 Weekly Orchestration

### Status

Accepted

### Context

Phase 4 requires dependable recurring weekly execution with observability, secrets management, and safe retries. Alternatives include a local cron job, a dedicated VM scheduler, or a CI platform.

### Decision

Use **GitHub Actions** as the primary orchestration and scheduling mechanism for weekly runs. The workflow will:

- trigger on a weekly `schedule` (cron) and support `workflow_dispatch` for manual runs
- run Phases 1 → 2 → 3 in order on `ubuntu-latest`
- store integration secrets in **GitHub repository secrets**
- upload phase outputs as **workflow artifacts** for audit and recovery

Local CLI execution remains supported for development and one-off debugging; it is not the primary recurring operations path.

### Why

- matches the weekly batch cadence without maintaining separate scheduler infrastructure
- provides built-in run history, logs, and artifact retention
- keeps secrets out of the repository and off individual laptops for production runs
- aligns with common team practices for scheduled data/ops jobs

### Consequences

- the repository must define `.github/workflows/weekly-review-advisory.yml` (or equivalent)
- operators need GitHub access to inspect failures and re-run workflows
- Groq daily limits and MCP availability still apply inside CI; failures must be visible in Actions logs
- overlapping manual and scheduled runs must be handled via workflow concurrency or operator discipline (see `docs/edge-case.md`)

## Decision 015: Add Phase 5 Web Frontend

### Status

**Accepted** (2026-05-21) — design references, hosting, and auth confirmed

### Context

Phases 1–4 deliver correct weekly artifacts via Python and GitHub Actions, but consumption still depends on JSON files, Docs, and Actions UI. Internal stakeholders need a browser-based weekly pulse; operators need run history without manual file hunting.

The user provided Stitch mockups and the **Executive Precision Dark** design system under `frontend references/stitch_groww_advisory_dashboard/` (see `docs/phases/phase-5/design-reference.md`).

### Decision

Add **Phase 5: Frontend & Operator Experience** after Phase 4. The frontend will:

- display the weekly pulse from `weekly_pulse.json` across three stakeholder routes matching Stitch: **Summary** (`/`), **Themes** (`/themes`), **Quotes** (`/quotes`)
- apply the **Executive Precision Dark** token set (Inter, `#131313` surfaces, semantic CRITICAL / WARNING / CONCERN chips)
- show run metadata and publication status on operator routes **`/runs`** and **`/runs/:runId`**
- use a **read-first** v1; optional `workflow_dispatch` via server-side API in v1.1

**Architecture:** **React 18 + Vite + TypeScript + Tailwind CSS** SPA, plus a **FastAPI** read API (Option 2). No Groq or MCP calls from the browser.

**References folder:** `frontend references/` (not shipped in production bundle; used for design parity during build).

**Hosting:** React SPA on **Vercel**; FastAPI read API on **Render** (`VITE_API_URL` points frontend to Render).

**Auth:** **None** — personal dashboard, no login gate (operator accepts public URL risk; no API keys in client).

**Themes page:** do **not** implement Stitch **prevalence %** or **Impact Analysis** widgets (out of scope for frontend and pipeline).

### Why

- improves adoption among non-technical stakeholders with an executive-grade dark UI already approved in mockups
- separates presentation from batch pipeline logic
- keeps secrets and Groq/MCP integration off the client

### Consequences

- new `frontend/` and `backend/review_advisory_api/` packages plus deploy pipeline
- Phase 4 should publish or index artifacts (`runs_index.json`) for UI refresh
- optional Phase 2 schema tweak: export `sentiment` on `top_themes[]` for Summary sentiment card
- severity chips use rank-based mapping until schema exports explicit severity

## Decision 016: Incremental Weekly Fetch with Rolling Review Warehouse

### Status

Accepted

### Context

Re-fetching eight weeks of store reviews every Monday is slow, skews App Store pagination, and re-processes the same reviews. Operators want weekly refreshes to pull **only new reviews**, merge with prior normalized data, analyze the **combined rolling corpus**, and keep **week-over-week pulse history**.

### Decision

- **Weekly fetch (scheduled):** 1-week lookback from public App Store + Play Store sources.
- **Rolling warehouse:** `data/warehouse/normalized_reviews.json` holds deduped reviews for an **8-week** window; older reviews are pruned on each merge.
- **Phase 1:** `--incremental` merges the new slice into the warehouse and rewrites the run's `normalized_reviews.json` to the merged corpus (reporting window metadata stays **8 weeks** for Phase 2).
- **Bootstrap:** `--bootstrap-warehouse` with 8-week fetch seeds the warehouse once.
- **History:** each Phase 2 `weekly_pulse.json` is archived under `data/history/weekly_pulse/<week-ending>/` with `data/history/runs_index.json`.
- **GitHub Actions:** default `run_mode=incremental`; successful runs commit `data/warehouse/` and `data/history/` to the repo.

### Why

- matches a natural weekly operations cadence
- reduces redundant fetch and Groq input churn
- preserves traceability and prior weekly pulses for comparison

### Consequences

- first incremental week may have a thin warehouse until bootstrap or several runs accumulate
- Actions needs `contents: write` to persist warehouse between runs
- Groq still analyzes the merged set (up to 1,000 cap), not isolated "new-only" theme diffing (future enhancement)
- see `docs/incremental-weekly-ingestion.md`

## What Belongs in This File

Record a decision here only when it materially affects one or more of the following:

- system architecture
- business workflow or operating model
- privacy and trust controls
- integration strategy
- delivery strategy or project governance

Each decision should include:

- a unique decision number
- status
- context
- decision
- why
- consequences
