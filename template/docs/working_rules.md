# Working rules

Standing process rules for the engineer and the agent: how to verify, how to phrase, where a
destructive command may point. A *law the system obeys* goes in `INVARIANTS.md`; a *mistake that has
already recurred* goes in `mistakes.md` (cross-referenced here, not repeated). Read the index; open
only the rules the work trips.

## Index

| # | Rule | Trips when you… |
|---|---|---|
| W1 | Verify absence from every angle before building **or delegating** | say "X is missing" |
| W2 | Read the code, not the spec or memory, for built behaviour | describe how X behaves |
| W3 | Ask the failure-window question first | touch an UNDERSTAND-IT trigger |
| W4 | Verify every number you cite | quote a count, amount, or status |
| W5 | Main session discusses; fresh agents execute and review | hand off work |
| W6 | A delegate STUBS an UNDERSTAND-IT surface, never builds it | scope a subagent |
| W7 | Name the database before any destructive SQL | type DROP / DELETE / TRUNCATE |
| W8 | Re-check branch and index before every commit; commit by path | `git add` / `git commit` |
| W9 | Irrevocable = ask first, every time | create/delete/send anything external |
| W10 | Guard ladder: a rule isn't done until it's a check that fails | add a rule or M-entry |
| W11 | One source of truth: import the definition, never restate it | write a predicate, formula, or constant that exists elsewhere |
| W12 | Handoff vs to-do: `NEXT-START-HERE.md` is rewritten, `NEXT.md` is never lossy | end a session |
| W13 | A delegate builds in its own worktree; a probe is undone from a copy, never `git checkout` | hand work to a subagent, or revert an experiment |
| W14 | Plan by tier: required and ratified for UNDERSTAND-IT, optional for delegate | start any piece of work |

---

## W1 — Verify absence from every angle
Before building something "missing", check: a handler under another name · logic inside another
component · deliberate reuse · deactivated (not absent) · a stub · not registered · meaning changed in
the authority. Build only when it is genuinely absent. **Verify, then delegate; never delegate the
verification.** (mistakes M1)

## W2 — Read the code for built behaviour
Specs describe intent; code describes reality. For "how does X behave", open the code and cite
`file::symbol`. Asserting a critical path's behaviour from memory has been wrong before.

## W3 — The failure-window question
For any UNDERSTAND-IT change, ask first: *what state is left if the process dies between
these two steps, and what resumes it?* Name the window before designing the fix.

## W4 — Verify every number
Every count, amount, or status in a summary comes from a command run this session. No remembered numbers.

## W5 — Main discusses, fresh agents execute
The main thread holds decisions and conclusions; exploration and review go to fresh agents so their
file dumps stay out of context and their judgement isn't anchored by the builder's.

## W6 — Delegates stub UNDERSTAND-IT surfaces
A subagent may write the scaffold and tests around an UNDERSTAND-IT path, but the owner reviews and
lands the core. `.claude/hooks/protect_paths.py` enforces this for paths in `.claude/protected_paths.txt`.

## W7 — Name the DB before destructive SQL
State which database (name + host) the statement will hit before running DROP / DELETE / TRUNCATE.

## W8 — Commit hygiene
Check `git branch --show-current` and `git status` immediately before committing. When sessions share a
checkout, commit by explicit path (`git commit -- <files>`), never `git commit -a`. Never revert a probe
with `git checkout <file>` on uncommitted work. (mistakes M5)

## W9 — Irrevocable = ask first
Payments, notifications, account/resource creation, deletes, deploys, migrations on shared data: explicit yes from the
owner for *that* action, at the time. Log what was created and how to clean it up. (mistakes M7)

## W10 — The guard ladder
Prose rule → test / scenario / hazard row that fails → hook that blocks. Move a rule up the ladder each
time it is broken. A rule that has recurred and is still only prose is unfinished work.

## W11 — One source of truth
If a predicate, formula, token, or SQL expression is defined somewhere, import it. Restated copies drift,
and the drift is silent. (mistakes M4)

## W12 — Handoff vs to-do
`NEXT-START-HERE.md`: a few lines, rewritten every session, enough to `/clear` and resume.
`NEXT.md`: everything to do and know, concise but never lossy.

## W13 — Delegates in worktrees; undo probes from a copy
A delegated agent gets its own worktree (`git worktree add -b <branch> <path>`, or the Agent tool's
`isolation: "worktree"`). To undo a temporary edit (a mutation probe, an experiment), restore the file
from a copy you made before the edit. `git checkout -- <file>` resets the whole file to the last commit
and silently deletes any uncommitted work in it.

## W14 — Plan by tier
UNDERSTAND-IT work starts with a plan in `docs/plans/` that names the trigger, the protected paths, the
source of truth, the failure window, and the mutation that must turn the test red. The owner ratifies it
before code is written; `review/verify.py --plans` enforces this mechanically. Delegated work may skip
the plan: there, fixtures and review catch mistakes, and a plan is overhead.

