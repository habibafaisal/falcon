# CASE-06 — `git checkout` as undo

**Class:** process. **Caught by:** the owner, mid-session; it had happened before.

## What happened
During mutation testing (mutate a line → run tests → confirm red → revert), the revert was
`git checkout <file>`. The file was tracked but its session's work was uncommitted. `checkout`
reverts the *whole file to HEAD* — it deleted the entire signature-verification build, not the
one-line mutation. A parallel revert on an untracked file failed silently, leaving a mutation on disk.

## Why every layer missed it
Scenarios, hazards and reviewers inspect the product. None watched *how the builder edits and reverts
files*. The probe loop had no safe-revert rule, and `git checkout <path>` looks surgical.

## The check that exists now
- **HAZARDS H8 / mistakes M5:** snapshot with `cp` before mutating, restore with `cp`; or commit first.
  The `sweep` operation bakes this in.
- **Hook** `no_stash_while_live.py`: blocks `git stash/checkout/reset` while a test run or another
  agent session is live in the repo. A prose rule had already failed; it moved up the guard ladder.

**Lesson:** when a rule is broken twice, it becomes a hook.
