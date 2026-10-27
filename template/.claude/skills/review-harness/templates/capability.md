---
capability: <slug>
capability_state: <vocab>
permitted_use: <vocab>
authority:
  - source: <path to the single source of truth for this claim>
    pointer: "<a locator — heading / §number / AC-id — to FIND it, never a copy of the ruling>"
governing_tests:
  - <path>
scenarios:
  S1: {status: demonstrated|inferred|contradicted|unverified, evidence: <path|null>, concern: <str|null>}
evidence_class: 0-5
executed: null   # ONLY verify.py may set this
---

# Capability: <name>

## Intent

- **Authority**: path + pointer (in frontmatter). The pointer is a locator, never a copy —
  the reviewer re-reads the source live so nothing here can go stale.
- **Business event**: what real event does this respond to?
- **Actors**: who calls it; who uses its output.
- **Output nature**: advisory | authoritative | executable — what does the output allow?
- **must_happen**:
- **must_never_happen**:

## Workflow states

| from | to | allowed by |
|---|---|---|
| | | |

## Scenario notes

Statuses live in the frontmatter. Notes here: why a scenario doesn't apply, or the concern behind a status.

## Evidence

- <artifact path> — what it shows, who wrote it, same origin as the code or not.

## Verdict

One paragraph, only after a verifier pass. Both axes plus what blocks the next gate.
Builder/verifier disagreements go here, side by side.

## Open questions for the human

- <judgment only: intent readings, hazards to accept, promotions>
