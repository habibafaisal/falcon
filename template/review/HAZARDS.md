# HAZARDS — cross-cutting risks

Risks that cut across capabilities. Each row says how it is found, what limits it today, and which
gate it blocks until fixed or accepted. Accepting an open hazard is a human decision (see GATES.md).

**Convention `verify.py` relies on:** a row is auto-run ONLY when its "found by" cell **leads** with a
backticked shell command. The command must OUTPUT MATCHES when the hazard is present (empty = clean).
Anything else — prose, a backtick mid-sentence, `judgment` — is a review-read: printed as `[SKIP]`,
never `[PASS]` (CASE-05).

| id | hazard | found by | limited by | blocks |
|---|---|---|---|---|
| H1 | float math where exact values are required (money, quantities) | `grep -rnE "float\(" app/ --include=*.py` | integer cents / Decimal policy | permitted_use ≥ shadow_mode |
| H2 | module-level mutable state on a control path | judgment | | |
| H3 | dependency lockfile drift | `git status --porcelain -- uv.lock package-lock.json` | | |
| H4 | shared-data query missing its tenant filter | judgment | | |
| H5 | control that lives only in memory (lost on restart) | judgment | | |
| H6 | same-origin evidence presented as independent | verify.py same-origin check (WARN) | auto-downgrade to class 4 | |
| H7 | external client tested only through a wholesale fake (P3) | judgment — for each `Fake<Vendor>` in tests, a real-client payload test exists | | permitted_use ≥ human_approved_live |
| H8 | mutation probe reverted with `git checkout/restore/reset` on an uncommitted file — deletes the whole uncommitted build | judgment — snapshot with `cp` first, restore with `cp` back; or commit before probing | no_stash_while_live + no_discard_uncommitted hooks | |
| H9 | an effect added to one door but not its twins (P4) | judgment | | |

Replace the H1/H3 commands with your stack's; delete rows that don't apply.
