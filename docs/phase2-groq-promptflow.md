# Phase 2 Groq Prompt Flow

## Purpose

This document defines the prompt flow for Phase 2 review intelligence using Groq. It translates the current Phase 2 architecture and implementation plan into a practical multi-step LLM strategy that can be implemented later without re-deciding the overall prompting approach.

The matching Python request and response contracts live in `phase-2/review_advisory_phase2/models.py`.

The prompt flow is intentionally designed around the current Phase 1 normalized dataset, which is:

- English-only
- emoji-free
- filtered to reviews with at least 7 words
- highly skewed toward Play Store reviews
- strongly polarized toward 1-star and 5-star ratings
- inconsistent in title availability, especially for Play Store reviews

Because of that shape, Groq should not receive the full weekly corpus in a single prompt. The system should use deterministic preparation first, cap the live working set at 1,000 reviews for the initial release, and then call Groq in staged passes.

## Goals

- extract a stable set of candidate themes from the normalized review dataset
- prevent prompt overload from the full weekly corpus
- keep outputs grounded in actual reviews
- make quote selection traceable
- produce a concise final weekly note that matches the Phase 2 and product constraints

## High-Level Flow

1. Deterministically slice and prepare evidence from the normalized review dataset.
2. Use Groq discovery prompts on smaller evidence batches to identify issue candidates.
3. Merge and consolidate the issue candidates into theme candidates.
4. Use Groq consolidation prompts to collapse overlapping themes and produce a ranked shortlist.
5. Build a curated final evidence set for the shortlisted themes.
6. Use a final Groq prompt to generate the weekly note, quotes, and action ideas in structured form.
7. Validate the output against guardrails before passing it to later phases.

## Why a Multi-Step Flow Is Needed

The current Phase 1 dataset contains `1435` normalized reviews, with `1269` from Play Store and `166` from App Store. Ratings are highly polarized, and many Play Store reviews do not have titles. This means:

- one broad prompt would be noisy and expensive in context terms
- source imbalance could cause one store to dominate if the prompt is unstructured
- long reviews could crowd out shorter but repeated patterns
- positive and negative feedback need separate treatment before final consolidation

## Groq Limit-Aware Constraints

The initial release should be designed around the following Groq limits for `llama-3.3-70b-versatile`:

- requests per minute: `30`
- requests per day: `1,000`
- tokens per minute: `12,000`
- tokens per day: `100,000`

In practice, token-per-minute is the more important runtime constraint for this workflow. The prompt flow should therefore:

- keep the live working set to `1,000` normalized reviews or fewer
- avoid sending the full capped set directly to Groq
- aim for around `10` Groq calls or fewer for one weekly run
- preserve a safety buffer below the token-per-minute limit for retries and final prompts

## Pre-Groq Deterministic Preparation

Before any Groq call, the system should prepare review evidence in a structured way.

### Recommended deterministic steps

- cap the live analysis set to 1,000 normalized reviews before any Groq call
- preserve all available App Store reviews while they fit within the cap
- allocate the remaining review budget to Play Store evidence using deterministic stratified selection
- prioritize `1-2` star reviews first, then `3` star reviews, then `4-5` star reviews
- partition reviews by source: App Store and Play Store
- partition reviews by rating band: `1-2`, `3`, `4-5`
- sort reviews within each slice by recency
- remove near-duplicates where the review body is materially identical
- create review snippets for long reviews while preserving the original full text for traceability
- compute basic frequency signals from repeated terms and bigrams
- identify likely complaint-heavy slices from `1-2` star reviews
- identify likely praise-heavy slices from `4-5` star reviews

### Suggested evidence unit

Each review passed into Groq should have:

- `review_id_hash`
- `source`
- `rating`
- `review_date`
- `title`
- `review_text`

Optional deterministic helper fields can also be passed:

- `slice_id`
- `word_count`
- `candidate_keywords`
- `duplicate_group_id`

## Prompt Stage 1: Theme Discovery

### Goal

Use Groq to identify issue patterns or praise patterns inside a constrained evidence slice.

### Input strategy

Run this prompt multiple times on smaller batches, for example:

- low-rating Play Store batches
- low-rating App Store batches
- neutral mixed batches
- high-rating praise batches

Each batch should contain enough reviews to show repetition, but not so many that the prompt becomes vague or exceeds the desired token budget. The goal of this step is not the final answer. It is to extract candidate themes with evidence.

Recommended operating target:

- target no more than `8` discovery calls for one weekly run
- keep each discovery batch small enough that total live throughput remains comfortably below the Groq TPM limit

### Expected output

Groq should return structured candidate themes with:

- provisional theme name
- short explanation
- sentiment direction: negative, positive, or mixed
- evidence review IDs
- why the issue seems recurring

### Discovery prompt template

```text
System:
You are analyzing app reviews for Groww. Your job is to identify recurring review patterns from the evidence provided.

Rules:
- Use only the reviews provided.
- Do not invent evidence, counts, trends, or quotes.
- Keep themes specific and operationally meaningful.
- Separate different problems unless they clearly belong together.
- Return valid JSON only.

User:
Context:
- App: Groww
- Batch type: {{batch_type}}
- Source: {{source_scope}}
- Rating band: {{rating_band}}
- Reporting window: {{start_date}} to {{end_date}}

Task:
Review the evidence and identify the most important recurring patterns in this batch.

For each candidate theme, return:
- theme_name
- sentiment
- summary
- evidence_review_ids
- recurrence_reason

Return JSON in this format:
{
  "batch_id": "{{batch_id}}",
  "candidate_themes": [
    {
      "theme_name": "",
      "sentiment": "negative|positive|mixed",
      "summary": "",
      "evidence_review_ids": [],
      "recurrence_reason": ""
    }
  ]
}

Evidence:
{{reviews_json}}
```

## Prompt Stage 2: Theme Consolidation

### Goal

Merge the candidate themes from many discovery batches into a small set of final theme candidates.

### Input strategy

This prompt should receive:

- the candidate themes from Stage 1
- summary metadata about each candidate theme
- optional deterministic aggregate signals such as counts or slice coverage

The consolidation prompt should not receive the entire raw review corpus again. It should receive the compressed candidate-theme layer plus a small set of top evidence references.

### Expected output

Groq should return:

- merged final theme candidates
- rationale for consolidation
- a shortlist of no more than 5 themes
- which themes are strongest for the week

### Consolidation prompt template

```text
System:
You are consolidating candidate review themes for Groww into a final shortlist.

Rules:
- Use only the candidate themes and evidence references provided.
- Merge overlapping themes only when they describe the same user problem or praise pattern.
- Do not create more than 5 final themes.
- Prefer business-readable names.
- Return valid JSON only.

User:
Context:
- Reporting window: {{start_date}} to {{end_date}}
- Total normalized reviews: {{review_count}}
- Source mix: {{source_mix}}

Task:
Consolidate the candidate themes into a final ranked shortlist.

For each final theme, return:
- final_theme_name
- sentiment
- summary
- supporting_candidate_theme_ids
- supporting_review_ids
- why_this_theme_matters

Return JSON in this format:
{
  "final_themes": [
    {
      "final_theme_name": "",
      "sentiment": "negative|positive|mixed",
      "summary": "",
      "supporting_candidate_theme_ids": [],
      "supporting_review_ids": [],
      "why_this_theme_matters": ""
    }
  ]
}

Candidate themes:
{{candidate_themes_json}}
```

## Prompt Stage 3: Final Weekly Note Generation

### Goal

Generate the final structured weekly pulse using only the curated final themes and verified evidence.

### Input strategy

This prompt should receive:

- the final ranked themes from Stage 2
- curated quote candidates for those themes
- summary metadata such as source mix and coverage limitations
- any final deterministic ranking or tie-break information

This step should not be responsible for discovering themes from scratch. It should only produce the final summary artifact.

### Expected output

Groq should return:

- a short opening summary
- top 3 themes
- 3 representative user quotes
- 3 action ideas
- optional short note on source coverage

### Final note prompt template

```text
System:
You are generating a concise weekly internal review advisory for Groww.

Rules:
- Use only the evidence and themes provided.
- Do not invent quotes.
- Keep the tone concise, factual, and useful for internal teams.
- Keep the total note brief and scannable.
- Return valid JSON only.

User:
Context:
- Reporting window: {{start_date}} to {{end_date}}
- Source mix: {{source_mix}}
- Coverage notes: {{coverage_notes}}

Task:
Generate the weekly review pulse.

Return JSON in this format:
{
  "opening_summary": "",
  "top_themes": [
    {
      "theme_name": "",
      "summary": ""
    }
  ],
  "user_quotes": [
    {
      "quote": "",
      "review_id_hash": "",
      "theme_name": ""
    }
  ],
  "action_ideas": [
    {
      "action": "",
      "linked_theme": ""
    }
  ],
  "coverage_note": ""
}

Final themes:
{{final_themes_json}}

Quote candidates:
{{quote_candidates_json}}
```

## Quote Selection Strategy Before the Final Prompt

Quote selection should be partially deterministic before the final Groq call.

### Suggested rules

- pick quotes only from reviews already linked to shortlisted themes
- avoid quotes with residual PII risk
- avoid excessively long quotes when a shorter representative quote exists
- avoid selecting all 3 quotes from the same theme unless one theme overwhelmingly dominates the week
- prefer quotes that state the issue clearly in user language

Groq should choose from curated quote candidates, not from the entire raw review set.

## Action-Idea Strategy Before the Final Prompt

Action ideas should also be grounded before Groq writes them.

### Suggested rules

- each action should be attached to one shortlisted theme
- actions should be phrased as internal recommendations, not guaranteed conclusions
- actions should remain specific enough to be useful, but not so detailed that they pretend roadmap certainty

Example action framing:

- investigate repeated complaints about chart responsiveness during high-volatility periods
- review support response expectations for users reporting delayed issue resolution
- evaluate whether brokerage and charges communication is clear enough at key user touchpoints

## Recommended JSON-First Workflow

Groq should return structured JSON at every stage. Do not ask Groq for free-form prose until the final rendering step, and even then, prefer a JSON payload that can be rendered deterministically afterward.

Why:

- easier validation
- easier retries
- easier comparison across runs
- lower risk of malformed weekly note structure

## Prompt Guardrails

Every Groq prompt in Phase 2 should reinforce these rules:

- use only the evidence provided
- do not invent quotes
- do not invent counts or trends
- do not exceed the theme limit
- keep language stakeholder-readable
- keep actions tied to evidence
- return structured JSON only

## Recommended Runtime Flow

1. Read the Phase 1 normalized dataset.
2. Cap the live working set to 1,000 reviews using the agreed prioritization rules.
3. Create deterministic slices and evidence batches.
4. Run Groq discovery prompts per batch.
5. Merge candidate themes deterministically where obvious duplicates exist.
6. Run the Groq consolidation prompt on the merged candidate set.
7. Build curated quote and action evidence inputs.
8. Run the final weekly note prompt.
9. Validate structure, quotes, and guardrails before publication.

## Known Risks

- source imbalance can skew discovered themes toward Play Store issues
- high-volume complaint batches can dominate if praise is not considered separately
- poorly batched evidence can cause Groq to merge unrelated issues
- overly broad consolidation prompts can collapse distinct problems into vague themes
- quote selection can drift if the final prompt is given too many candidates
- repeated prompt experimentation can spend the daily Groq token budget quickly if dry runs are not used first

## Success Criteria for This Prompt Flow

- Groq outputs no more than 5 final themes
- quotes remain traceable to real review IDs
- themes are stable across similar weekly inputs
- actions are evidence-backed rather than generic
- the final note can be rendered into the required weekly pulse format without major manual rewriting
