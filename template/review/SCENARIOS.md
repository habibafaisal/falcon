# SCENARIOS — standing failure scenarios

Every capability is judged against these. Each relevant one is marked in the capability file:
**demonstrated** (evidence file exists), **inferred** (argued from code), **contradicted**, or
**unverified**.

| id | scenario |
|---|---|
| S1 | **Wrong rule** — code is internally correct but implements the wrong thing. Would the authority quote catch the difference? |
| S2 | **Circular evidence** — the test's expected values came from the code's own output. Would anything fail if the code was wrong from day one? |
| S3 | **Never built** — a needed property (scoping, durable control, lockfile, audit record) simply doesn't exist. What proves it does? |
| S4 | **Computed = allowed** — a calculated value is treated as permission to act. Where is the gate between computing and acting? |
| S5 | **Crash mid-write** — process dies halfway. What state is left; does resume duplicate or lose work? |
| S6 | **Same input twice** — is the effect applied once? |
| S7 | **Boundary crossing** — data or actions leak between tenants/actors/scopes. What stops it, everywhere? |
| S8 | **Silent partial failure** — some items in a batch fail but the batch reports success. How would anyone know which? |
| S9 | **Can't see, can't stop** — it misbehaves in use. Can it be spotted, halted, recovered without losing data? |
| S10 | **Environment drift** — a dependency, schema, or config differs from what was reviewed. Would that be caught before it runs? |

## Evidence principles (learned from escapes — they apply to every scenario above)

| id | principle | born from |
|---|---|---|
| P1 | **Canonical fixture.** Any money split, priority, or ordering rule is pinned by expected values worked out BY HAND from the authority's formula — at an input where the rival readings produce *different* numbers. A balanced ledger sums to zero under either ordering, so balance alone never proves priority. | CASE-01 |
| P2 | **Red-ability.** A test offered as evidence for an UNDERSTAND-IT invariant counts only once it is shown to FAIL with the guard inverted: mutate the constant/branch, see red, revert from a snapshot. Green-under-mutation = a false all-clear; the scenario stays `unverified`. | CASE-02 |
| P3 | **Real wire, not just the fake.** A fake that replaces an external client wholesale proves orchestration, not the contract. Each fake needs a sibling test that drives the REAL client over a mocked transport and asserts the outgoing request body and types. | CASE-03 |
| P4 | **Parity per effect, not per row.** When several doors (webhook, cron sweep, retry, manual) see the same authoritative fact, each must produce the same *effect* — ledger entry, state change — not merely the same record. A new effect added to one door is added to all, or carries a written reason. | CASE-04 |
| P5 | **Verify the verifier.** A `[PASS]` is only meaningful if the check ran. Tooling that certifies other work gets its own red-ability tests; "not run" must print differently from "clean". | CASE-05 |
