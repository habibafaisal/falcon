---
name: review-harness
description: Review and verify agent-built work with an evidence-graded harness. Use when the user wants to review or verify a capability an agent built, instantiate a review layer in a repo (review/ folder), run a capability review with a fresh-context verifier, record a review escape (a miss a human caught), or asks about gates, evidence classes, or promotion of a capability. Triggers - "review this capability", "init the review harness", "record an escape", "is this actually done", "run a capability review".
---

# Review Harness

Passing tests do not prove the system is right. This skill sets up and runs a review
layer that automates every check a script or fresh agent can settle, so the human only
spends time on judgment calls.

## Core ideas

**Four lenses** — every review checks all four:
1. **Intent** — right business problem? Point at the single source of truth and re-read it live.
2. **Behavior** — does the code produce the intended result?
3. **Architecture** — safe under real conditions (isolation, exact arithmetic, durability, retries)?
4. **Operations** — can it be stopped, watched, and recovered?

**Nothing is ever "done".** A verdict states two things:
- `capability_state`: not_started → implemented → integrated → exercised → validated → operational
- `permitted_use`: prototype_only → demo_only → historical_backtest → shadow_mode → human_approved_live → automated_live

Example: *"validated for historical_backtest; blocked on: S4 unverified, two controls in-memory only."*
What each promotion needs lives in `review/GATES.md` as data.

**Evidence classes 0–5** (lower = stronger):
| Class | Evidence |
|---|---|
| 0 | matches outside reality (actuals, an authority ruling) |
| 1 | an invariant holds (totals conserved, replay byte-identical) |
| 2 | independently written fixture agrees |
| 3 | test survives a mutation probe (see the `sweep` operation) |
| 4 | test written in the same commit/session as the code |
| 5 | "it runs" |

If test, code, and fixture come from the same commit/session, the class is 4 at best —
the expected values may just be the code's own output written down.

**The builder never verifies.** If this session wrote the code, a fresh subagent reviews it.

**Every human-caught miss becomes an escape** plus a new check, in the same session.

## Operations

Templates live in this skill directory under `templates/` and `agents/capability-reviewer.md`.

### `init` — set up `review/` in the current repo

1. Create `review/` with `capabilities/` and `escapes/` subdirectories.
2. Copy `templates/GATES.md`, `templates/HAZARDS.md`, `templates/SCENARIOS.md` into `review/`.
3. Ask the user for the **single source of truth** — the one authority that overrides on
   meaning/critical values/rulings (e.g. a product spec, a domain expert's rulings log), and the executable
   contract that stands only where that authority is silent (e.g. `spec/`, an OpenAPI file). Write both paths into GATES.md.
4. If `review/verify.py` is missing, copy it from Falcon's template and set `source_dir` and
   `test_command` in `review/falcon.toml`. Its one rule: only verify.py may set `executed:`.

### `review <change-or-area>` — review one capability

1. Work out WHICH capability the change or area affects. A capability is a business
   outcome (e.g. "seal a reproducible backtest") — never a module, helper, or commit.
   Only create a new capability file if the change truly serves a new business outcome.
2. Create `review/capabilities/<name>.md` from `templates/capability.md` if missing,
   else update it. Authority = path + pointer (a locator), never a copied quote —
   the reviewer re-reads the source live so the file can never go stale.
3. If `review/verify.py` exists, run it and capture the output. Never set `executed:` by hand.
4. Dispatch a fresh subagent with `agents/capability-reviewer.md` as its prompt, plus the
   capability file and verify.py output. The builder never verifies. Do not soften or pre-answer its challenges.
5. Merge the verifier's verdict into the capability file, AND append a `review_log` entry per
   scenario just reviewed: `{scenario, reviewed_commit: <the commit the reviewer actually
   examined>, reviewed_at, verdict}`. If the verifier disagrees with a builder claim, record
   both sides — never quietly pick one.
6. Show the human the verdict plus the open questions. Flag anything that matches a
   human-checkpoint decision type in GATES.md.

### `sweep` — mutation-sweep a capability's `red_ability` (evidence class 3)

Green tests only prove "trusted green" if you have shown the suite goes RED when the guard
is actually broken. This mode does that on a schedule the human triggers — never a cron, never
an autonomous run against UNDERSTAND-IT code. A capability records the probe in its frontmatter:

```yaml
red_ability:
  status: proven | unproven | not_applicable   # not_applicable = no single mechanical guard to mutate
  last_swept: "YYYY-MM-DD"
  mutation: "<file> — <the exact one-line weakening> → <which tests go RED, and the failure mode>"
```

Run by a **fresh agent the human starts** (weekly, or before promoting an UNDERSTAND-IT capability):

1. Pick the capability (or sweep every `red_ability.status: proven` file that is stale by the
   human's cadence). Read its `red_ability.mutation` — that string IS the recipe.
2. Establish the baseline: run the capability's `governing_tests`, confirm GREEN. If already red,
   STOP and report — there is nothing to prove until the suite is green.
3. **Snapshot the target file to a scratchpad copy first** (`cp <file> <scratch>/<file>.bak`).
   Apply the mutation from the recipe. NEVER revert with `git checkout`/`restore`/`reset <path>` —
   those revert to HEAD and delete any uncommitted work (recurring hazard). Revert only by copying
   the snapshot back.
4. Re-run the governing_tests. Confirm the named tests go RED with the recorded failure mode. If
   they stay green, the mutation no longer bites — the guard moved or the test rotted: record
   `status: unproven`, flag it to the human, do NOT stamp a fresh `last_swept`.
5. Revert from the snapshot. Re-run once more, confirm GREEN restored. Only now update
   `last_swept` to today. If a test's name or failure mode drifted, update the `mutation` string too.
6. Report: which capabilities swept, which stayed proven, which regressed to `unproven`.

Concurrency: this runs tests, so it collides with any other pytest/verify.py run against the shared
test DB — sweep alone, or against an isolated per-run test DB.

### `escape` — record a miss a human caught

1. Pick the next id `ESC-YYYY-NNN` from the files in `review/escapes/`.
2. Create the file from `templates/escape.md`: what was missed, why the harness missed
   it, and the new check it implies.
3. Add that new check in the same session — a new scenario, hazard row, or template
   field. An escape without a new check is incomplete.
4. In affected capability files, mark the related scenarios `unverified` until re-reviewed.
