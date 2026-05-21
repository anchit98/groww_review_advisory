# Edge Cases

## Purpose

This document captures the most important edge cases for the Review Advisory Agent based on the current documentation set, including the problem statement, architecture, implementation plan, phase evaluations, and major project decisions.

The goal of this file is to make unusual or failure-prone scenarios explicit before they appear during implementation, testing, or weekly operation. It should be used as a planning and review aid across all phases of the project.

## How to Use This File

- use it while refining architecture and delivery scope
- use it alongside each phase `eval.md` file during testing
- use it when updating `docs/decision.md` after a major project-level choice
- use it during operator review to decide whether a run is safe to trust

This file is focused on edge conditions, not normal behavior. It does not replace architecture, implementation planning, or phase evaluation criteria.

## Global Handling Principles

The following principles apply to every edge case in this project:

- never bypass MCP for Google Docs or Gmail to work around a failure
- never include PII in prompts, outputs, documents, drafts, or logs
- never publish a low-confidence or structurally invalid weekly note
- never silently ignore major data quality or publication failures
- preserve human review before outbound sharing in the initial release
- prefer failing clearly over producing a misleading summary

## Cross-Cutting Edge Cases

### 1. Not Enough Review Volume for a Useful Weekly Pulse

If the available review set for the reporting window is too small, the system may produce weak or misleading themes.

Expected handling:

- flag the run as low-confidence
- avoid overstating trends
- allow a reduced-confidence summary only if the output clearly reflects the low sample size
- if necessary, stop publication and require operator review

Why this matters:

- a small dataset can create false urgency or false reassurance

### 2. Review Volume Is Extremely High

If the weekly window contains far more reviews than expected, the system may struggle with prioritization, consistency, or runtime behavior.

Expected handling:

- preserve summarization constraints despite high volume
- ensure the top themes still reflect the most important issues rather than random sampling noise
- maintain stable run observability so operators can see if scale affected the run

Why this matters:

- high volume should not reduce output quality or cause the workflow to become unpredictable

### 3. One App Store Dominates the Dataset

One source may contribute most of the reviews in a given week, making the combined output look representative when it is actually skewed.

Expected handling:

- preserve source traceability in the review set
- avoid implying balanced cross-store sentiment if one store dominates
- consider including source-aware context in internal review where relevant

Why this matters:

- decision-makers may assume the summary reflects both platforms equally when it does not

### 4. The Reporting Window Has No Valid Reviews

Inputs may exist, but after validation, deduplication, and privacy filtering, there may be no usable reviews left.

Expected handling:

- stop the run gracefully
- record the reason clearly
- do not generate a fabricated empty summary
- do not create a misleading Google Doc or Gmail draft

Why this matters:

- empty input is an operational event, not a valid insight outcome

## Data Ingestion Edge Cases

### 5. App Store and Play Store Source Formats Change

Public store-accessible review sources may change structure, column names, or date formatting over time.

Expected handling:

- detect format mismatches early in ingestion
- fail clearly rather than misreading columns silently
- record which source failed and why

Why this matters:

- silent schema drift can poison every downstream stage

### 5A. App Store Public Pagination Does Not Reach the Full 8-Week Window

The public Apple review feed may not expose enough pages to cover the full requested 8-week range for a high-volume app like Groww.

Expected handling:

- store the newest publicly reachable reviews instead of fabricating missing coverage
- record the coverage gap in fetch metadata and run warnings
- preserve the earliest available review date so downstream readers can judge the actual window covered

Why this matters:

- the system should be transparent about partial public-source coverage rather than implying full historical completeness

### 6. Required Fields Are Missing

Some rows may be missing rating, review text, title, or review date.

Expected handling:

- reject or flag records that cannot support downstream analysis safely
- tolerate missing optional fields only when the review remains useful
- surface record drop counts in logs

Why this matters:

- incomplete data can weaken theme quality and traceability

### 7. Optional Fields Are Missing in Large Numbers

Even when ingestion succeeds, large gaps in optional fields can reduce the usefulness of the final summary.

Expected handling:

- continue only if the remaining data still supports meaningful analysis
- make coverage limitations visible during internal review

Why this matters:

- technically valid input may still be weak from a business perspective

### 8. Duplicate Reviews Appear Across Files or Runs

The same review may be present multiple times because of export overlap or repeated ingestion.

Expected handling:

- apply stable duplicate handling rules
- prevent repeated reviews from artificially boosting a theme
- make duplicate logic auditable

Why this matters:

- duplicates distort frequency and severity signals

### 9. Review Dates Are Malformed or Ambiguous

Date values may appear in inconsistent formats or time zones.

Expected handling:

- parse dates using a consistent standard
- reject records that cannot be assigned to the correct reporting window
- avoid accidental inclusion of stale or future-dated reviews

Why this matters:

- time window errors directly affect weekly trend credibility

### 10. Reviews Fall Just Outside the Target 8-Week Window

Boundary conditions may include or exclude reviews inconsistently.

Expected handling:

- define inclusive and exclusive boundary rules explicitly
- keep window logic stable across runs
- test the exact cutoff dates during evaluation

Why this matters:

- edge-date inconsistency makes trend comparison unreliable

### 11. Mixed-Language Reviews Appear

The dataset may include reviews in more than one language.

Expected handling:

- retain only English-language reviews in the normalized dataset
- drop reviews identified as non-English before later phases consume them
- when language metadata is missing, use the Phase 1 English-detection rule rather than keeping everything

Why this matters:

- mixed-language inputs can distort clustering and reduce downstream theme quality

### 12. Review Text Is Extremely Short

Some reviews may be only one or two words, such as "bad" or "great app."

Expected handling:

- remove reviews with 6 words or fewer during Phase 1 normalization
- keep the normalized working set biased toward higher-signal feedback
- record how many short reviews were excluded

Why this matters:

- short reviews often add sentiment but not enough diagnostic detail

### 12A. Reviews Contain Emojis or Emoji-Only Noise

Some reviews may contain emojis mixed into otherwise valid text, while others may be mostly emoji noise.

Expected handling:

- strip emojis from titles and review text before normalized storage
- drop the review if little or no meaningful text remains after emoji removal and sanitization
- record emoji-removal counts in Phase 1 stats

Why this matters:

- emojis add noise to normalization and can make downstream text handling less stable

### 13. Review Text Is Extremely Long

Some reviews may contain long narratives, multiple complaints, or unrelated details.

Expected handling:

- preserve meaning without letting long reviews dominate clustering
- select quotes carefully so only the relevant part is represented

Why this matters:

- long reviews can overpower shorter but more common signals

## Privacy and Content Safety Edge Cases

### 14. A Review Contains Email Addresses, Names, IDs, or Other PII

Raw review content may contain user-provided sensitive details.

Expected handling:

- mask or exclude the risky content before downstream use
- ensure no raw PII reaches prompts, outputs, documents, drafts, or logs

Why this matters:

- privacy violations directly conflict with project requirements and trust goals

### 15. PII Appears Inside a Quote Candidate

A quote may be representative but also contain personally identifiable content.

Expected handling:

- do not use the quote as-is
- either sanitize it safely or choose another representative quote
- never prioritize evidence quality over privacy compliance

Why this matters:

- quotes are highly visible in final artifacts and therefore high risk

### 16. A Review Includes Sensitive Operational or Financial Details

Even if a review does not contain classic PII, it may contain account-specific, transaction-specific, or complaint escalation details.

Expected handling:

- treat sensitive contextual details conservatively
- avoid publishing details that create privacy, security, or compliance risk

Why this matters:

- the absence of email or name fields does not mean content is safe to publish

### 17. Harmful, Abusive, or Offensive Language Appears

Reviews may contain profanity, insults, threats, or hateful language.

Expected handling:

- avoid reproducing abusive text unless there is a very strong reason and it can be safely sanitized
- preserve the underlying issue without amplifying harmful language

Why this matters:

- internal teams need the signal, not necessarily the raw toxic phrasing

## Analysis and Theme Generation Edge Cases

### 18. The Same Underlying Issue Appears in Many Different Words

Users may describe one product problem using different wording, making clustering harder.

Expected handling:

- group semantically similar feedback into one coherent theme where justified
- avoid fragmenting one major issue into multiple minor buckets

Why this matters:

- fragmented themes reduce actionability and hide scale

### 19. Different Issues Get Merged Into One Theme

Theme generation may over-compress feedback and combine unrelated complaints.

Expected handling:

- keep theme naming specific enough to stay meaningful
- split themes when the merged issues imply different actions or stakeholders

Why this matters:

- over-merging produces vague summaries and weak action ideas

### 20. More Than Five Plausible Themes Exist

A busy week may naturally produce more than five meaningful issue areas.

Expected handling:

- prioritize and compress to the most important five at the analysis layer
- ensure the final note still focuses on the top three themes
- avoid silently dropping important high-severity issues without review

Why this matters:

- the project explicitly caps theme count to preserve clarity and scannability

### 21. Themes Are Valid but Poorly Named

A theme may be technically correct but labeled too vaguely or too internally.

Expected handling:

- use stakeholder-readable labels
- avoid ambiguous names like "general issues" or overly technical jargon

Why this matters:

- poor naming reduces the usefulness of the final advisory even when clustering is otherwise good

### 22. Positive and Negative Sentiment Are Mixed in One Theme

Users may discuss the same area with opposite sentiment.

Expected handling:

- preserve nuance when the same product area generates both praise and complaints
- avoid flattening mixed sentiment into a misleading one-sided statement

Why this matters:

- mixed feedback can indicate partial success, inconsistent experiences, or rollout variance

### 23. One Viral or Emotional Review Dominates Perception

A dramatic review may appear more important than it really is because of language intensity.

Expected handling:

- rank themes by repeated evidence, not just emotional phrasing
- avoid letting one memorable review distort the summary

Why this matters:

- stakeholders need recurrence-driven insight, not anecdotal overreaction

### 24. Low-Signal Noise Crowds Out Actionable Issues

Generic praise, repetitive comments, or very shallow complaints may consume attention.

Expected handling:

- deprioritize low-information reviews when selecting themes and quotes
- ensure the weekly note rewards actionable patterns over noise

Why this matters:

- the system is supposed to support prioritization, not just compress text

### 25. The Same Theme Persists for Many Weeks

A recurring issue may continue over multiple cycles.

Expected handling:

- avoid presenting a chronic issue as if it is brand new every week
- preserve enough run context for internal users to recognize persistent problems

Why this matters:

- repeated blind rediscovery reduces stakeholder confidence in the system

## Quote Selection Edge Cases

### 26. No Quote Is Cleanly Representative

The strongest available quotes may be too vague, too long, too sensitive, or too unique.

Expected handling:

- choose evidence conservatively
- prefer accurate but modest quotes over dramatic but misleading ones
- do not invent or over-edit a quote to force fit the summary

Why this matters:

- quote quality strongly influences perceived trustworthiness

### 27. A Quote Changes Meaning When Trimmed

Shortening a quote for readability may remove important nuance.

Expected handling:

- trim only when meaning remains faithful
- choose another quote if safe trimming is not possible

Why this matters:

- a distorted quote is effectively a fabricated one

### 28. Three Quotes All Reflect the Same Theme

The quote set may accidentally over-focus on one theme while ignoring others.

Expected handling:

- distribute quotes across the most important issues when possible
- use concentrated quoting only if one theme truly dominates the week

Why this matters:

- quote variety affects how stakeholders interpret the breadth of issues

## Action Idea Edge Cases

### 29. Action Ideas Are Generic

Generated actions may sound reasonable but offer little prioritization value.

Expected handling:

- tie each action idea back to specific review patterns
- avoid vague advice such as "improve user experience" unless grounded in a clear problem area

Why this matters:

- generic actions make the advisory less useful for product teams

### 30. Action Ideas Are Not Supported by Evidence

The system may propose a plausible next step that is not justified by the actual reviews.

Expected handling:

- prefer evidence-backed restraint over speculative recommendations
- reject unsupported action ideas during output review

Why this matters:

- unsupported recommendations reduce credibility and can misdirect stakeholder attention

### 31. Action Ideas Are Too Large for a Weekly Pulse

Recommendations may become strategic program proposals instead of actionable weekly guidance.

Expected handling:

- keep actions concise and right-sized for a summary artifact
- reserve larger strategic interpretation for separate planning discussions

Why this matters:

- the weekly pulse is for signal and direction, not full roadmap design

## Weekly Note Composition Edge Cases

### 32. The Summary Exceeds 250 Words

The generated note may drift beyond the target word budget.

Expected handling:

- enforce the concise format as a hard quality guardrail
- compress wording without dropping essential evidence

Why this matters:

- the summary is intended to be read quickly by busy stakeholders

### 33. The Note Is Structurally Incomplete

The output may omit themes, quotes, or action ideas.

Expected handling:

- fail validation before publication
- do not publish an incomplete note as if it were a normal weekly pulse

Why this matters:

- incomplete structure breaks the expected stakeholder contract

### 34. The Note Sounds Confident Despite Weak Evidence

Generated language may appear stronger than the underlying data justifies.

Expected handling:

- moderate tone when the evidence base is weak or skewed
- avoid definitive statements when the data does not support them

Why this matters:

- overconfident summaries are dangerous because they are easy to trust

### 35. The Output Reads Like Generic AI Text

The note may become abstract, repetitive, or detached from the actual reviews.

Expected handling:

- preserve evidence grounding
- keep wording specific to the observed user feedback
- prefer concise internal-advisory language over generic summarization language

Why this matters:

- stakeholders need usable insight, not polished filler

## MCP Integration Edge Cases

### 36. Google Docs MCP Server Is Unavailable

The system may complete analysis but fail during publication because the Google Docs MCP server is not reachable.

Expected handling:

- record the failure clearly
- do not silently drop the publish step
- preserve the validated note so publication can be retried safely

Why this matters:

- publication failure should not erase successful upstream work

### 37. Gmail MCP Server Is Unavailable

The system may create the document but fail to create the draft email.

Expected handling:

- preserve partial success state
- record that Google Docs succeeded and Gmail failed
- support safe follow-up action rather than restarting blindly

Why this matters:

- partial publish states are operationally common and must remain understandable

### 38. MCP Permissions Are Insufficient

The MCP server may be reachable but lack the required access to create or update artifacts.

Expected handling:

- surface the permission issue explicitly
- avoid ambiguous failure messages
- do not introduce a direct API workaround

Why this matters:

- the project decision is MCP-only, so permission gaps must be handled within that model

### 39. The Google Doc Is Created but Formatted Poorly

The content may publish successfully but become hard to read in the destination document.

Expected handling:

- treat readability as part of publication quality
- review whether the published format still matches the intended weekly pulse structure

Why this matters:

- technically successful publication can still fail the business goal

### 40. Gmail Draft Content Does Not Match the Google Doc

The document and email may drift in structure or content across the same run.

Expected handling:

- ensure both artifacts are based on the same validated note
- treat content mismatch as a publication quality issue

Why this matters:

- stakeholders may lose trust if different channels tell slightly different stories

### 41. Re-Running the Same Week Creates Duplicates

A repeated run may create multiple documents or multiple drafts for the same reporting period.

Expected handling:

- define and follow a clear repeated-run policy
- make duplicate behavior predictable and visible

Why this matters:

- duplicate artifacts create confusion and reduce operational cleanliness

## Orchestration and Operational Edge Cases

### 42. A Run Fails Midway Through

The workflow may fail after ingestion, after analysis, or during publication.

Expected handling:

- record the exact stage of failure
- preserve useful intermediate state where appropriate
- avoid forcing a full blind restart when targeted recovery is possible

Why this matters:

- stage-specific failure visibility is central to Phase 4 readiness

### 43. A Scheduled Run and a Manual Run Overlap

Two runs may target the same reporting period at nearly the same time.

Expected handling:

- detect overlapping execution where possible
- prevent conflicting outputs or unclear ownership of the final artifact set

Why this matters:

- overlapping runs can produce duplicated or inconsistent outputs

### 44. Configuration Changes Break a Weekly Run

Changes in reporting window assumptions, recipient settings, or environment setup may create unexpected failures.

Expected handling:

- make configuration-sensitive failures obvious
- ensure operators can distinguish configuration issues from logic failures

Why this matters:

- configuration drift is a common operational failure mode in recurring systems

### 45. Logs Exist but Do Not Explain the Failure

The system may technically log events but still leave operators unable to diagnose what happened.

Expected handling:

- capture enough context to identify whether failure came from input data, analysis quality, validation, or MCP publication
- treat poor observability as a release-readiness issue

Why this matters:

- weak logs turn small incidents into expensive support work

### 46. Operator Review Is Skipped Informally

Even if the system creates drafts rather than sending automatically, teams may start trusting outputs without proper review.

Expected handling:

- keep the human review step visible in the operating model
- make it clear that draft creation is not the same as business approval

Why this matters:

- trust controls are part of the solution, not optional process decoration

## Decision-Driven Edge Cases

### 47. Someone Tries to Add a Direct API Fallback

A future builder may try to bypass MCP to make publication easier.

Expected handling:

- reject the change unless the project decisions are intentionally revised
- update `docs/decision.md` only if the project truly changes direction

Why this matters:

- this would violate a major architectural decision already documented

### 48. Someone Wants Real-Time Monitoring Instead of Weekly Pulse

Stakeholders may expand the scope after seeing early outputs.

Expected handling:

- treat it as a separate product direction, not a quiet scope creep
- document the change as a major decision if accepted

Why this matters:

- weekly batch processing is a foundational project decision

### 49. Stakeholders Want More Than Five Themes or a Longer Note

Business users may ask for a richer output after seeing the first concise version.

Expected handling:

- evaluate the request against the original scannability goal
- treat the change as a major decision if it materially alters summary behavior

Why this matters:

- format discipline is part of the current trust and usability model

### 50. Teams Start Treating the Agent as a Final Decision-Maker

Stakeholders may over-trust the advisory and skip human judgment.

Expected handling:

- reinforce that the output is a structured advisory, not an autonomous business authority
- keep human review and interpretation explicit in the operating model

Why this matters:

- the project is designed to support decisions, not replace them

## Phase Mapping

### Phase 1 Critical Edge Cases

- source format drift
- missing required fields
- duplicate reviews
- malformed dates
- empty usable dataset
- PII in raw content

### Phase 2 Critical Edge Cases

- too many plausible themes
- theme fragmentation or over-merging
- weak quote representativeness
- unsupported action ideas
- overconfident summaries
- word-limit failure

### Phase 3 Critical Edge Cases

- MCP unavailability
- MCP permission issues
- partial publication success
- duplicate documents or drafts on re-run
- content mismatch between Google Docs and Gmail draft

### Phase 4 Critical Edge Cases

- overlapping runs (scheduled cron + manual `workflow_dispatch` at the same time)
- GitHub Actions secret missing or rotated without updating the workflow
- Groq or MCP failures inside CI with limited retry visibility
- workflow timeout or job cancellation mid-pipeline
- artifact retention expiry before an operator downloads evidence
- unclear failure ownership (which phase job/step failed)
- poor re-run behavior (duplicate Doc appends on full re-run)
- weak runbook quality
- operator confusion during recovery

### 46A. GitHub Actions Scheduled Run Overlaps a Manual Run

A weekly cron job may start while an operator has triggered `workflow_dispatch` for the same reporting period.

Expected handling:

- use workflow `concurrency` (e.g. `group: weekly-pulse`) to queue or cancel overlapping runs when possible
- document that operators should avoid parallel runs for the same week unless intentionally testing
- record distinct phase `run_id` values per workflow run so outputs remain distinguishable

### 46B. GitHub Actions Secret Missing or Invalid

The workflow may start but fail when `GROQ_API_KEY`, `GOOGLE_DOC_ID`, or `GMAIL_DRAFT_TO` is unset.

Expected handling:

- fail fast at the step that needs the secret with a clear log message
- do not print secret values in logs
- document required secrets in the Phase 4 runbook

### 46C. CI Network or Cold-Start Failure on MCP Server

The hosted MCP server (e.g. on Render) may be cold or unreachable from GitHub-hosted runners.

Expected handling:

- surface HTTP errors in the Phase 3 step log
- preserve Phase 1–2 artifacts on the workflow run for retry
- allow re-running only Phase 3 when `weekly_pulse.json` already exists

### 47A. Phase 5 UI Shows Stale or Missing Run Data

The dashboard reads `data/history/runs_index.json` and archived pulse files. If Phase 4 does not commit history or `sync_runs_index.py` is skipped, the UI shows an empty state.

Expected handling:

- empty state on `/` and `/runs` with operator guidance (run pipeline, sync index)
- week selector only lists indexed runs; default to latest successful entry
- do not fabricate pulse content when `weekly_pulse.json` is missing

### 47B. Phase 5 UI Must Not Expose Secrets or PII

The browser bundle and API responses are untrusted display surfaces.

Expected handling:

- API returns only public metadata fields (no `GROQ_API_KEY`, MCP tokens, or `.env`)
- optional server-side PII pattern filter on quotes and coverage text before JSON is served
- `review_id_hash` only — never raw store reviewer identifiers
- Phase 3 `partial_success` and publication errors visible on run detail (not hidden as green success)

### 47C. Failed Phase 2 Run in Run History

A run may appear in the index with Phase 2 `failed` or missing pulse.

Expected handling:

- run history shows status badges per phase
- pulse routes show error state instead of empty themes when pulse file is absent
- do not reuse a previous week's pulse for a failed run id

## Exit-Gate Questions for Edge-Case Readiness

Before a phase is considered complete, the team should be able to answer:

- what are the most likely failure modes in this phase?
- which edge cases fail safely, and which require operator intervention?
- which edge cases can produce misleading output rather than obvious failure?
- how will the team know from logs or review evidence that an edge case occurred?
- which edge cases should block progression to the next phase?

## Maintenance Guidance

Update this file when:

- a new major failure mode is discovered during evaluation
- a new decision in `docs/decision.md` changes system behavior
- a phase evaluation introduces a new quality gate
- operators encounter recurring production-like issues during testing

This file should evolve with the project, but it should stay focused on meaningful edge conditions rather than becoming a generic issue list.
