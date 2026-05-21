# Phase 2 Evaluation

## Phase Goal

Validate that the system can turn normalized reviews into a concise, useful, and trustworthy weekly advisory note with strong evidence grounding.

## What Must Be Tested

- reviews are grouped into no more than 5 meaningful themes
- the top themes are ranked in a way that reflects real review patterns
- selected quotes are genuine and representative
- action ideas are relevant to the observed feedback
- the final note remains concise and follows the required structure
- the output excludes PII and unsupported claims

## Test Scenarios

### Functional Tests

- generate a weekly note from a representative review set and confirm the required structure is present
- confirm the note contains top themes, 3 quotes, and 3 action ideas
- confirm the output stays within the target word limit

### Quality Tests

- compare generated themes against a manually reviewed sample set
- verify quotes are exact or safely trimmed from real reviews without changing meaning
- verify each action idea can be traced back to one or more observed review patterns
- confirm low-signal noise does not dominate the final note

### Guardrail Tests

- confirm the system does not generate more than 5 themes
- confirm no invented metrics, fabricated quotes, or unsupported trends appear
- confirm PII filters still hold in prompts and final outputs

### Regression Tests

- run the same input set multiple times and confirm results stay acceptably stable
- test datasets with skewed sentiment to ensure the summary still prioritizes correctly

## Evidence Required

- sample weekly note outputs
- prompt and response validation results
- manual review notes for at least one representative dataset
- examples showing quote-to-source traceability

## Exit Criteria

- theme quality is judged acceptable on representative sample data
- all included quotes are traceable to real source reviews
- action ideas are grounded and useful to stakeholders
- note format is consistent and stays within the concise target
- no PII or unsupported claims appear in evaluated outputs

## Phase Sign-Off Question

Can stakeholders read the generated note and trust it enough to use it as an internal weekly advisory?
