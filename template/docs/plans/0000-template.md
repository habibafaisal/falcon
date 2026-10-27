---
plan: <short-slug>
tier: understand-it          # understand-it | delegate
trigger: <which row of the CLAUDE.md tier table, e.g. critical computation>
status: proposed             # proposed | ratified  (only the owner sets ratified)
ratified_by: <owner, date>
protected_paths:             # every protected path this work will touch; `verify.py --plans` checks it
  - <src/ledger/>
source_of_truth: <path + heading of the spec or ruling this must agree with>
red_mutation: <the one-line change that must turn the governing test red, e.g. "drop the rounding step">
---

# <Title>

Copy this file to `docs/plans/NNNN-<slug>.md`. **Required for UNDERSTAND-IT work** and ratified by the
owner before any code is written. Optional for delegated work, where a few lines or no plan is fine.

## Goal
What changes for the user or the system, in two lines.

## Design, one concept at a time
The pieces, in the order the owner should hear them. Name the industry pattern if one fits.

## Failure window
What happens if this fails halfway, or runs twice? What state is left behind, and who notices?

## Tests (written first)
- Expected values derived by hand from `source_of_truth`, not copied from the code's output.
- The governing test, and proof it goes red under `red_mutation`.

## Steps
1. …

## Out of scope
What this plan deliberately does not do.
