# Phase 2 Groq Analysis

This folder contains the Phase 2 Groq analysis package for the Review Advisory Agent.

The implementation follows the prompt flow documented in `docs/phase2-groq-promptflow.md` and includes:

- deterministic preprocessing of the Phase 1 normalized dataset
- deterministic capping to a 1,000-review working set before live Groq analysis
- discovery-batch generation from smaller evidence slices rather than the entire working set
- Groq prompt rendering for discovery, consolidation, and final note generation
- Pydantic request and response contracts
- dry-run artifact generation
- live Groq execution when `GROQ_API_KEY` is available
- lightweight request and token pacing for Groq live runs

## Package

- `review_advisory_phase2/models.py` contains the Pydantic request and response models
- `review_advisory_phase2/pipeline.py` contains the Phase 2 orchestration and Groq integration
- `review_advisory_phase2/__main__.py` exposes the CLI
- `tests/` contains model and pipeline tests

## Dry Run

From the `phase-2` folder:

```bash
python -m review_advisory_phase2 \
  --normalized-reviews ../phase-1/output/phase1-2026-05-11-f0813bdc/normalized_reviews.json \
  --phase1-metadata ../phase-1/output/phase1-2026-05-11-f0813bdc/run_metadata.json \
  --output-dir output \
  --dry-run
```

This validates the Phase 1 handoff, prepares the capped working set plus discovery evidence batches, and writes prompt artifacts without calling Groq.

## Live Groq Run

Add `GROQ_API_KEY` to the repo-root `.env` file or set it in your shell, then run:

```bash
python -m review_advisory_phase2 \
  --normalized-reviews ../phase-1/output/phase1-2026-05-11-f0813bdc/normalized_reviews.json \
  --phase1-metadata ../phase-1/output/phase1-2026-05-11-f0813bdc/run_metadata.json \
  --output-dir output
```

The Phase 2 runtime auto-loads `.env` files from the current directory, the `phase-2` directory, or the repo root before checking `GROQ_API_KEY`.

Optional:

- `--groq-model <model-name>` to override the default Groq model

## Runtime Guardrails

The live Phase 2 runtime is intentionally conservative for `llama-3.3-70b-versatile`:

- maximum working set: `1,000` normalized reviews
- discovery call target: `8` calls or fewer
- consolidation calls: `1`
- final note calls: `1`
- soft pacing target: about `4` requests per minute and `10,000` tokens per minute

Dry runs also write a `working_review_set.json` artifact so the deterministic review cap can be inspected separately from the full prepared evidence file.

## How to Print the Schemas

From the `phase-2` folder:

```bash
python -m review_advisory_phase2 --print-schemas
```

This prints the JSON schema bundle for all Phase 2 request and response models.
