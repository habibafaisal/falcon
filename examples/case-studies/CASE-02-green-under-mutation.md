# CASE-02 — Green under mutation

**Class:** integrity · evidence. **Caught by:** a fresh, non-builder review that mutated the guard.

## What happened
A build's headline safety property: event type A (a recovery) must **never** change list B (a risk
watchlist). The capability file called it "mechanically enforced."

The reviewer added one value to the constant that encodes the rule — making recoveries eligible as
the watchlist's anchor — and re-ran the suite. **17/17 green.** Nothing guarded the invariant.

## Why every layer missed it
- The code was actually correct. The **test** was the gap: it checked watchlist *membership*, but the
  inverted rule only changes the answer when money moves *between* the two events. The fixture moved
  no money in that gap, so right and wrong code produced identical output.
- Second time in the same build: an earlier test asserted byte-identity on an object the scenario
  never created. Same class — a test whose subject cannot exhibit the failure it claims to guard.

## The check that exists now
- A test with a payment in the gap, proven to go **red** under the mutation.
- **SCENARIOS P2 (red-ability):** an UNDERSTAND-IT invariant isn't demonstrated until its test is
  shown failing with the guard inverted. The `sweep` operation of the review-harness skill re-runs
  these probes on demand and records them in the capability file (`red_ability:`).

**Lesson:** a green test proves nothing until you've seen it red.
