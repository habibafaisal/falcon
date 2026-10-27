# INVARIANTS — the law

Numbered rules the system must obey regardless of implementation. Each names what it protects and how
it is enforced (DB constraint, test, hook, review-read). Supersede in place with a dated marker;
never renumber.

| # | Invariant | Protects | Enforced by |
|---|---|---|---|
| 1 | <e.g. every ledger journal balances to zero, or is refused> | correctness | <DB trigger + test> |
| 2 | <e.g. a job's side effect is applied at most once per idempotency key> | exactly-once | <unique index + test> |
| 3 | <e.g. every read of a record passes the tenant/permission check> | isolation | <query helper + test> |
| 4 | <e.g. audit events are append-only and hash-chained from a genesis row> | integrity | <trigger + verify CLI> |
| 5 | <e.g. AI output is parsed once, frozen, and never re-consulted by a decision path> | determinism | <test> |
