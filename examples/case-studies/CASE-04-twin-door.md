# CASE-04 — Same fact, two doors, one effect

**Class:** money · architectural-boundary. **Caught by:** the owner, running a $1 sandbox transfer and
watching the ledger against the bank balance.

## What happened
A bank event can arrive two ways: a **webhook** (seconds) and a **scheduled sweep** (minutes). A
standing ruling said both doors behave the same. Both did write the same reconciliation *record* —
but only the sweep posted the **ledger journal**. Between the webhook and the next sweep the books
sat $1 above the bank.

| Step | Ledger cash | Bank |
|---|---|---|
| webhook: transfer settled | 100.00 | 99.00 ← mismatch |
| sweep runs, posts journal | 99.00 | 99.00 |

In-session, the agent first explained it away as "timing". The owner named the ruling it broke.

## Why every layer missed it
- Parity was tested **per row** (same record from every door), never **per effect** (same money movement).
- The journal was added later to the sweep only; its design compared against other sweep phases,
  never against the webhook.
- The fresh review was scoped to "is the sweep correct?" — it was, in isolation.
- This was the second time: fix one door, forget its twin — one layer up.

## The check that exists now
- **SCENARIOS P4 (parity per effect)**, **HAZARDS H9**, **mistakes M4** (recurrence recorded).
- The capability's scenario marked `contradicted` until a test shows the webhook alone posts exactly
  one journal and the next sweep is a no-op.

**Lesson:** reviewers don't know your domain. You test as an operator, with real (sandbox) money.
