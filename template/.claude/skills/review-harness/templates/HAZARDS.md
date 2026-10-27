# HAZARDS — cross-cutting risks

Risks that cut across capabilities. Each row says how it is found (a command verify.py
can run, or `judgment`), what limits it today, and which gate it blocks until fixed or
accepted. Accepting an open hazard is a human decision (see GATES.md).

| id | hazard | found by (cmd or `judgment`) | limited by | blocks |
|---|---|---|---|---|
| H1 | float math where exact values are required (money, quantities) | `<grep cmd>` | <e.g. integer-cents policy> | <e.g. permitted_use ≥ historical_backtest> |
| H2 | module-level mutable state on a control path | `<grep cmd>` | | |
| H3 | dependency lockfile drift | `<check cmd>` | | |
| H4 | shared-data query missing its tenant filter | `<scan cmd>` or `judgment` | | |
| H5 | control that lives only in memory (lost on restart) | `judgment` | | |
| H6 | same-origin evidence presented as independent | `<git-history check>` | auto-downgrade to class 4 | |
