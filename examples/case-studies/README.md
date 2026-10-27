# Case studies — misses that became checks

Sanitized escapes from the money-movement platform Falcon was extracted from. The domain is money; each
failure class (tests agreeing with wrong code, forgiving fakes, twin doors, a lying verifier) shows up
in any careful project. Client names, vendors,
code paths and amounts are removed or replaced with illustrative numbers; the failure mechanism is
unchanged. Each one: what happened → why every automated layer missed it → the check that exists now.

| Case | The miss | Layer that failed | Check added |
|---|---|---|---|
| [CASE-01](CASE-01-tests-agreed-with-wrong-code.md) | Money split shipped with priority inverted | test-first + fresh review | SCENARIOS P1 — hand-derived canonical fixture |
| [CASE-02](CASE-02-green-under-mutation.md) | Headline invariant's test stayed green with the guard inverted | test suite | SCENARIOS P2 — red-ability / `sweep` |
| [CASE-03](CASE-03-forgiving-fake.md) | 14 tests passed against a fake; the live call was rejected | mocks / TDD | SCENARIOS P3, HAZARDS H7 |
| [CASE-04](CASE-04-twin-door.md) | Webhook and sweep wrote the same row but only one booked the money | per-path tests | SCENARIOS P4, HAZARDS H9, mistakes M4 |
| [CASE-05](CASE-05-verifier-lied.md) | The gatekeeper certified checks it never ran | the verifier itself | P5 + verify.py fixes + tests |
| [CASE-06](CASE-06-checkout-wiped-build.md) | `git checkout` as "undo" deleted an uncommitted build | process (no layer watched it) | HAZARDS H8, mistakes M5, `no_stash_while_live` hook |

The common thread: every one passed the tests written by the same agent that wrote the code.
