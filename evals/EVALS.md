# Evaluation: theme discovery quality (Phase 2 pipeline)

**Run evaluated:** `phase2-2026-05-21-a592cc6c` (1,437 ingested reviews, 8-week window, Llama 3.3 70B via Groq)
**Reproduce:** `python evals/run_theme_eval.py` (offline, reads the stored run; no API calls)

## Method and honest limitations
- **Annotator:** labels were assigned in a single pass by an LLM annotator (Claude) and are listed in the script for audit. They have **not** been double-labelled by a human. Treat the numbers as a first-pass estimate with wide uncertainty (n=57 and n=39).
- **Question 1, precision:** is each review cited as evidence for a theme actually about that theme?
- **Question 2, coverage:** of negative reviews (rating ≤ 2) *not* cited by any theme, how many would a reader assign to one of the 5 final themes? Random sample, seed 7.
- This is not a recall estimate over the whole corpus: it only measures reviews the pipeline did not already cite.

## Results
| Metric | Result |
|---|---|
| Theme-assignment precision (strict / lenient) | 41/57 = **72%** / 43/57 = 75% |
| Per theme (strict) | Support 80%, **Technical/Performance 32%**, Brokerage 100%, Ease of use 88%, Features 100% |
| Reviews cited under more than one theme | 11 of 57 evidence slots (46 unique reviews) |
| Coverage of uncited negative reviews | 23/39 = **59%**; 41% belong to no surfaced theme |
| Reviews seen by theme discovery | 145 of 1,437 ingested (**10%**); 1,000 analysed after capping |
| Themes surfaced in the leadership pulse | 3 of 5 final themes |
| User quotes verbatim-grounded in source | 3 of 3 |

## What the eval found
1. **The "Technical Issues" theme is contaminated.** 11 of its 19 evidence reviews are brokerage-charge complaints, the same IDs as the "High Brokerage Charges" theme. Its summary bullets in the pulse include "High brokerage charges" and "Hidden fees", and one of its user quotes is about brokerage and interface. A leader reading the pulse would overstate technical instability.
2. **Real complaint areas are missing.** Uncovered negatives cluster in login/KYC/onboarding, funds withdrawal, data accuracy (wrong P&L, wrong 52-week high/low) and trust/mis-selling.
3. **Discovery sees about a tenth of the data.** Themes are proposed from 145 reviews, so rare but severe issues can be missed.
4. **Misleading coverage note.** The report says "No play_store source file was supplied" while 1,229 of 1,437 reviews are Play Store.

## Changes this suggests (not yet implemented)
- Assign each review one primary theme (or enforce a de-duplication step) before computing theme size.
- Add a validation pass: every bullet, quote and action must be entailed by reviews assigned to that theme.
- Stratify discovery batches by rating, source and week instead of taking the head of the file.
- Add a recurring "unexplained negatives" bucket so uncovered clusters surface instead of vanishing.
- Fix the coverage-note logic.

After implementing these, re-run this script on a new week and report the delta.
