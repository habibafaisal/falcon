# <Project> — Working Agreement

@NEXT-START-HERE.md

> **First run.** If this file still contains `<Project>`, setup isn't done. Before any other work, run
> the `falcon-setup` skill: it interviews the owner and fills in this file, the protected paths, and
> `review/` with the owner's own choices. The skill deletes this block when it finishes.

## What this is

<2–5 lines: what the system does, what must never break.> The map is `ARCHITECTURE.md` — ask the
`oracle` agent instead of reading it into context. The law is `INVARIANTS.md`. Decisions are
`docs/adr/`. Process rules are `docs/working_rules.md`. Recurring mistakes are `docs/mistakes.md`.

## Commands

- **Install:** `<cmd>` · **Tests:** `<cmd>` · **Lint:** `<cmd>`
- **Review gate:** `python review/verify.py [capability-slug]` · **Map freshness:** `python review/verify.py --map`

## Who owns what — risk-tiered ownership

The owner (<name>) owns architecture and system understanding. AI generates code; the owner must
understand and approve the parts where a silent bug is expensive.

The line is a **trigger set, not a file list**: anything touching the triggers below is UNDERSTAND-IT,
however much it *looks* like boilerplate. "It's just a table / one API call" is the trap.

| Component | Mode | What a silent bug costs |
|---|---|---|
| Boilerplate, read-only UI, CRUD, adapters, code with good fixtures | **Delegate** — fixtures and the screen catch mistakes | a visible bug |
| **Critical computation** (<e.g. amounts, doses, scores, metrics people act on>) | **UNDERSTAND IT** | a wrong number nobody notices |
| **Identity** (<e.g. dedup keys, record matching, tenant resolution>) | **UNDERSTAND IT** | two real entities silently merged or split |
| **Integrity / trust** (<e.g. permission checks, audit log, schema contracts>) | **UNDERSTAND IT** | a check that *looks* enforced and isn't |
| **Exactly-once / determinism** (<e.g. retries, idempotent jobs, replay>) | **UNDERSTAND IT** | an effect applied twice, or a result that won't reproduce |
| **Irreversible actions** (<e.g. payments, notifications, deletes, deploys>) | **ASK FIRST, every time** | can't be undone |

Replace the `<e.g.>` examples with your domain's (see Falcon's README → "Pick your triggers"). `.claude/protected_paths.txt` mirrors this table mechanically: delegated
subagents cannot write those paths.

**For UNDERSTAND-IT work:**
0. **Plan first.** Write `docs/plans/NNNN-<slug>.md` from the template, and wait until the owner ratifies
   it before writing code. Only the owner sets `status: ratified` (the `human_ratifies` hook refuses an
   agent that tries), and every `review/verify.py` run fails on a protected-path change with no ratified
   plan. For delegated work a plan is optional.
1. Walk the owner through the design **one concept at a time** before writing code; get their mental
   model first ("how would you approach this?").
2. Name the domain term of art as it comes up (one line, not a lecture).
3. Afterwards, have the owner explain it back; point out gaps with targeted questions.
4. **Engagement watchdog:** after ~3 passive accepts in a row ("ok", "go ahead", silent approvals),
   pause and ask the owner to explain what was just done and why.
5. A design decision is recorded as an ADR in `docs/adr/` and ratified by the owner the session it is made.

On delegated work, move fast — don't quiz the owner on mechanical parts.

## Review layer (do without being asked)

- **Before building:** ask the `oracle` (where does it live, which invariant, built or not); read the
  index of `docs/mistakes.md` and `docs/working_rules.md` and only the entries the work trips; read any
  `review/capabilities/` file the work touches — its open questions are constraints.
- **Delegated agents work in their own git worktree,** never in the main checkout, so their edits can't
  collide with the owner's or another agent's uncommitted work (W13).
- **While building:** test-first. For UNDERSTAND-IT work, expected values are derived by hand
  from the authority's formula, not copied from the code's output (SCENARIOS P1).
- **After building:** run `review/verify.py` (it includes the plan gate); then the `review-harness` skill in `review` mode — a
  **fresh agent** reviews; the builder never verifies its own work. Prove load-bearing tests go red
  under mutation (`sweep`, P2).
- **When the owner catches a miss:** `review-harness` `escape` mode — record it, and add a new check
  (test, scenario, hazard row, or hook) **in the same session**. If it recurred, add an M-entry to
  `docs/mistakes.md`. A miss that produces only a note will happen again.
- **Guard ladder:** a rule isn't done until it's a check that fails. Prose → test/scenario → hook.
- When a change touches module boundaries or a ruling, update `ARCHITECTURE.md` in the same change.

## Behavioural guidelines

- **Irrevocable = ask first.** Never create, delete, send, or move anything that can't be undone without
  the owner's explicit yes for that action. Approval doesn't carry over to the next action.
- **Verify before claiming absence.** "X is missing" needs a search for it under other names first.
- **Read the code, not memory,** for how a built critical path behaves.
- **Simplicity first — except integrity guards.** Guards against the "impossible" (a forged record, a
  double-applied effect) *are* the product. Never strip one citing simplicity.
- **Surgical changes;** narrate every deletion.
- **Surfacing a finding:** lead with its class — product-meaning · architectural-boundary ·
  integrity risk · mechanical cleanup · dead code — then Problem · Why it matters · Decision needed ·
  Safe default · Blocks current work (y/n).

## Session continuity

`NEXT-START-HERE.md` (imported above) is the **handoff**: a few lines on what the next session does and
must-know guards — rewrite it, never append. `NEXT.md` is the full, never-lossy to-do list. Durable
state lives in the repo, never in session memory: a ruling that only exists in chat is not durable —
write it into `INVARIANTS.md` or an ADR the session it is made.
