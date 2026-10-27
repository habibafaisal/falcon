# The Falcon method

General-purpose agent harnesses make code match its spec, and they spend the same process on every
change. On a careful project that isn't enough. Code that is correct by its own tests can still be wrong about the
thing that matters (an amount, a dose, a permission, a record's identity), because the same agent
wrote the reading of the spec, the test, and the code.

The examples below come from a money platform, where Falcon was built. Swap in your own domain's
triggers (README → "Pick your triggers").

Falcon is built from **loops**. Each loop below says what it is, what failure it exists for, and which
files implement it. Read one at a time.

---

## Loop 1 — Risk-tiered ownership

**What:** every piece of work is tiered by *what a silent bug would cost*, not by how hard it looks.
Boilerplate is delegated. Changes that hit a **trigger** (critical computation, identity, integrity,
exactly-once/determinism, irreversible actions) are **UNDERSTAND-IT**: the human owner hears the design one concept at a time, gives their own mental
model first, ratifies the decision as an ADR, and explains it back afterwards. Planning follows the
tier: UNDERSTAND-IT work starts from a plan in `docs/plans/` (trigger, protected paths, source of truth,
failure window, the mutation that must turn the test red), ratified before code is written and
enforced by `verify.py --plans`. Delegated work may skip the plan. If the owner accepts
~3 things in a row without engaging, the agent stops and asks them to explain.

**Failure it prevents:** autonomy-first harnesses minimise the human, so the human's understanding of
the system decays until nobody can say why the critical parts behave the way they do.

**Files:** `template/CLAUDE.md` (the ownership table), `template/docs/adr/`, `template/docs/plans/`,
`verify.py --plans`.

## Loop 2 — Orient through an oracle, not file dumps

**What:** a read-only `oracle` agent holds the map (`ARCHITECTURE.md`, `INVARIANTS.md`) and answers
"where does X live, which invariant governs it, is it built?" with `file::symbol` + invariant + build
state. Exploration goes to fresh agents; the main thread keeps conclusions only. `verify.py --map`
fails when the map cites paths that no longer exist.

**Failure it prevents:** the census trap — rebuilding something that already exists under another
name (mistakes M1) — and stale maps steering new sessions.

**Files:** `template/.claude/agents/oracle.md`, `template/ARCHITECTURE.md`, `verify.py --map`.

## Loop 3 — Evidence is graded, not "passing"

**What:** nothing is "done". A capability (a business outcome, not a module) has two axes —
`capability_state` (implemented → … → operational) and `permitted_use` (prototype → … →
automated_live) — and its evidence is graded 0–5. A test written in the same session as the code is
class 4 at best: its expected values may just be the code's output written down. Critical computations need
**hand-derived fixtures** at inputs where rival readings disagree (P1).

**Failure it prevents:** tests that agree with wrong code (CASE-01).

**Files:** `template/review/GATES.md`, `SCENARIOS.md`, `capabilities/`, `verify.py` (schema,
same-origin flag, only it may stamp `executed:`).

## Loop 4 — The builder never verifies

**What:** after building, a **fresh agent** that knows nothing the builder knew reviews against four
lenses (intent, workflow, architecture, operations), re-reads the authority live, and must name a
mutation that should turn a test red. Builder and verifier disagreements are recorded side by side.

**Failure it prevents:** self-review — the builder's misreading of the spec survives its own review.

**Files:** `template/.claude/skills/review-harness/` (`review` operation,
`agents/capability-reviewer.md`).

## Loop 5 — Red-ability: see it fail

**What:** a test for a load-bearing invariant counts only after it's been shown red with the guard
inverted. The `sweep` operation snapshots the file, applies the recorded mutation, confirms red,
restores from the snapshot (never `git checkout`), confirms green, and stamps `red_ability`.

**Failure it prevents:** vacuous green tests (CASE-02), and fakes more forgiving than reality
(CASE-03, P3).

**Files:** review-harness `sweep`, capability frontmatter `red_ability:`.

## Loop 6 — Every miss becomes a check

**What:** when the human catches something every automated layer let through, it's recorded as an
**escape** — what happened, why each layer missed it — and is incomplete until it ships a new check
**in the same session**: a test, a scenario, a hazard row, or a hook. The second time a mistake class
happens, it becomes an M-entry in `docs/mistakes.md`.

**Failure it prevents:** learnings that become notes the next agent never reads. Notes aren't enforcement.

**Files:** review-harness `escape`, `template/review/escapes/`, `template/docs/mistakes.md`,
`examples/case-studies/`.

## Loop 7 — The guard ladder

**What:** a rule climbs: prose in CLAUDE.md → a check that fails (test, scenario, hazard scan) → a hook
that blocks at the tool boundary. Each time a rule is broken, it moves up a rung.

- `protect_paths.py` — a delegated subagent can't write the paths in `.claude/protected_paths.txt`;
  the main session always can. Each path carries its named invalidation.
- `no_stash_while_live.py` — no `git stash/checkout/reset` while tests or another session are live.
- `no_discard_uncommitted.py` — no `git checkout/restore` of a file with uncommitted changes, or
  `reset --hard` over them, at any time (CASE-07).
- `human_ratifies.py` — no agent, main session included, can set a plan to `status: ratified`.
- `next_md_size.py` — soft nudge when the to-do file bloats.

**Failure it prevents:** agents skip prompt-level rules under pressure (CASE-06 broke a prose rule twice).

**Files:** `template/.claude/settings.json`, `template/.claude/hooks/`.

## Loop 8 — The human tests as an operator

**What:** the owner exercises the system the way a real operator would (sandbox transactions,
reversals, awkward edge cases) and compares the system's view against an outside source of truth
(the bank statement, the lab result, the provider's console). This is where most escapes come from.

**Failure it prevents:** reviewers that don't know the domain. A code reviewer catches smells, not
"the ledger is $1 above the bank between the webhook and the sweep" (CASE-04).

**Files:** `template/review/OPERATOR_SESSION.md`: the source of truth, awkward cases to try, a totals-level
diff table, and an optional Claude-in-Chrome pass where Claude drives the UI and the human signs the diff.
Its output feeds Loop 6.

## Loop 9 — Continuity outside the model

**What:** durable state lives in the repo. `NEXT-START-HERE.md` is a short handoff rewritten every
session; `NEXT.md` is the full, never-lossy to-do; rulings go into `INVARIANTS.md` or an ADR the
session they're made.

**Failure it prevents:** decisions that exist only in chat memory and silently vanish on `/clear`.

---

## Honest limits

- The fence is **fail-open** by design (an unparseable payload is allowed) and only fences subagents.
  It's a delegation guard, not a security boundary. It can be switched off (`FALCON_FENCE=off`); if you
  do, record why.
- Hooks bind Claude Code only. A human or another tool can still do anything.
- `human_ratifies` guards the status line and textual Bash. An agent can still edit other lines of an
  already-ratified plan; the plan's git history is the backstop.
- `verify.py` assumes Python + pytest-style output; other stacks need `test_command` and the summary
  parser adapted.
- Loop 1 and Loop 8 cost human time. That's the point on trigger paths, and waste elsewhere — so the tier
  table decides where it's spent.
