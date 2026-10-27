# Plans

One file per piece of work, `NNNN-<slug>.md`, from `0000-template.md`.

- **UNDERSTAND-IT work:** a plan is required, and the owner sets `status: ratified` before code is
  written. `python review/verify.py --plans` fails if a protected path changed without a ratified plan
  that lists it.
- **Delegated work:** a plan is optional.

A plan says what we're about to do. A decision that outlives the work goes in an ADR (`docs/adr/`).
