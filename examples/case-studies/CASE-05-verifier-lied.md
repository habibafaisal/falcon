# CASE-05 — The verifier certified checks it never ran

**Class:** integrity · the harness itself. **Caught by:** an independent agent reviewing the harness.

## What happened
`review/verify.py` — the gatekeeper that stamps every capability — had two false-cleans:

1. **Hazards it never ran printed `[PASS] clean`.** The parser took the first backtick in a table
   cell as a shell command. In two rows that backtick was a filename and a word in a sentence. Run as
   commands, they errored with empty output — and empty output was the same signal as "detection
   found nothing."
2. **`executed:` was stamped even on FAIL.** The stamp was a bare timestamp, which everyone read as
   green. Two capabilities with schema failures sat behind fresh-looking stamps.

## Why every layer missed it
Nothing verified the verifier. Every other component got a fresh reviewer and mutation probes; the
tool's own `[PASS]` was trusted.

## The check that exists now
- A hazard row runs only if its cell **leads** with the command; anything else prints `[SKIP]
  review-read`, never `[PASS]`.
- The stamp carries the outcome: `executed: "<ts> verify.py PASS|FAIL"`.
- Both pinned by tests in `tests/test_verify.py`. **SCENARIOS P5.**

**Lesson:** "not run" must never look like "clean". The forgery you guard against can live in the guard.
