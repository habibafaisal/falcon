# CASE-07 — The harness wasn't running on itself

**Class:** process. **Caught by:** the builder itself, a few seconds later. **When:** while building
Falcon's own plan gate. This is CASE-06 again, in the repo that ships the fix for CASE-06.

## What happened
The agent building Falcon ran a mutation probe on `verify.py`: break one line, run the tests, watch
them go red, undo. It undid the break with `git checkout -- verify.py`. The plan-gate code it had just
written in that file was uncommitted, so the checkout reset the whole file to the last commit and
deleted it. The tests had gone red, as intended, so the probe looked like a success. Only a follow-up
`git diff` showed the file had no changes left. The code was rebuilt, and the probe was redone by
restoring from a copy.

## Why every layer missed it
- **The rule existed** (mistakes M5, HAZARDS H8: snapshot with `cp`, restore with `cp`). The builder
  didn't apply it. A prose rule failed again, as CASE-06 predicted.
- **The hook existed, but wasn't installed.** Falcon's repo didn't run Falcon's own hooks, so nothing
  stood between the agent and the command.
- **The hook would have let it through anyway.** `no_stash_while_live` only blocks `git checkout`
  while pytest or another session is live. The probe ran the tests first and checked out after they
  finished. HAZARDS H8 had marked the hook "(partial)", and this was the gap.

## The check that exists now
- **Hook `no_discard_uncommitted.py`:** denies `git checkout/restore <path>` when that path has
  uncommitted changes, and `git reset --hard` over a dirty tree, whatever else is running. It follows a
  `cd` earlier in the same command, which is how the original command was written. Tests:
  `tests/test_hooks.py`, including that exact command shape.
- **Falcon runs its own Bash hooks:** the repo root has `.claude/settings.json` wiring
  `no_stash_while_live` and `no_discard_uncommitted` from `template/`.
- HAZARDS H8 is no longer partial; M5 names both hooks.

**Lesson:** a harness that doesn't run on its own repo is only prose to the people building it. And a
hook scoped to *when* the danger usually happens misses the time it happens anyway; guard the
condition itself (uncommitted changes), not a proxy for it (tests running).
