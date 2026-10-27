---
name: falcon-setup
description: First-run interview that fills in Falcon's placeholders with the owner's own choices. Use when CLAUDE.md still contains "<Project>", or when the owner says "set up falcon", "run falcon setup", or "redo the ownership tiers".
---

# Falcon setup

Falcon was just copied into this repo, and its files are still templates. This skill interviews the
owner and fills them in. **Claude proposes; the owner decides.** Never fill a row the owner hasn't
answered, and never write a default in their name.

Ask **one question at a time**. Wait for the answer before asking the next.

## Step 1 — The project

1. What does this project do, in two lines?
2. What must never break? (The one thing that would hurt most if it were silently wrong.)
3. Commands: install, tests, lint. (Read `package.json` / `pyproject.toml` / `Makefile` first and
   propose them. The owner confirms or corrects.)
4. Where does production code live? (Goes into `review/falcon.toml` → `source_dir`.)
5. What is the single source of truth for what the system *should* do (a spec, a ruling doc, a
   product owner)? (Goes into `review/GATES.md` → "Intent sources".)

## Step 2 — Choose how to pick the ownership tiers

Offer both modes and let the owner pick. Say the trade-off in one line each:

- **A. Start from scratch.** The owner names their own triggers. This is slower, but it makes them
  think about what a silent bug would cost in *this* project.
- **B. Strike out the defaults.** Show Falcon's default rows and let the owner keep, edit, or strike
  each one. This is faster, but it risks keeping a default without thinking. So for every row the
  owner keeps, ask for a one-line reason.

### Mode A — from scratch

1. "Name the parts of this system where a bug could be wrong *without anyone noticing*." Collect a
   list in the owner's words.
2. For each item, ask: "What would a silent bug here cost?" Write that into the "What a silent bug
   costs" column.
3. Ask: "Which actions can't be undone (payments, sends, deletes, deploys)?" Each becomes an
   **ASK FIRST** row.
4. Everything not named is **Delegate**. Read the final table back and ask the owner to confirm.
5. Only after that, mention any default category they didn't name (critical computation, identity,
   integrity, exactly-once, irreversible). Ask: "Deliberately left out, or missed?" Record the answer.

### Mode B — strike out the defaults

Walk the rows of the tier table in `CLAUDE.md` one at a time:

- **Critical computation**, **Identity**, **Integrity / trust**, **Exactly-once / determinism**:
  Keep, edit, or strike? If kept, which concrete code is it in this project, and why does it belong?
- **Irreversible actions:** which actions, concretely?
- **Anything to add** that the defaults don't cover?

A row the owner can't give a reason for is **struck**, not kept "to be safe". An unexplained row
trains everyone to ignore the table.

## Step 3 — Protected paths

For each UNDERSTAND-IT row, ask which files or directories hold it. Write each one to
`.claude/protected_paths.txt` **with its named invalidation** (what a delegate could silently break
there). If the owner can't name one, the path doesn't go in. If the code doesn't exist yet (a new
project), write `# TODO(<row>): add paths when the code exists` and add it to `NEXT.md`.

## Step 4 — Which loops to keep

Ask: "Does this project have any UNDERSTAND-IT rows?"

- **Yes:** keep every loop.
- **No (a low-stakes project):** offer the light set: Loop 9 (handoff + `NEXT.md`), `docs/mistakes.md`,
  and tests. Ask whether to keep the oracle, the fresh-agent review, and `verify.py`. Write the answer
  into the "Review layer" section of `CLAUDE.md` as a one-line scope rule, e.g. *"Review layer applies
  only to changes that touch an UNDERSTAND-IT row; everything else: run the tests."*

## Step 5 — Write it down

1. Fill `CLAUDE.md`: the project name and lines, commands, the owner's name, and the tier table as
   decided. Remove every `<e.g.>` and `<...>` placeholder. If a section was declined, remove it.
2. Fill `review/falcon.toml` (`source_dir`, `test_command`) and `review/GATES.md` (intent sources).
3. Write `docs/adr/0001-ownership-tiers.md` from `docs/adr/0000-template.md`, with:
   - which mode was used (A or B), and why the owner chose it;
   - every row kept, with its reason;
   - every default category struck or left out, with the reason ("deliberately", or "missed, then
     added");
   - the loop scope from Step 4.

   Set the status to **Proposed**. It becomes **Ratified** only when the owner says so.
4. Delete the **First run** block at the top of `CLAUDE.md`.
5. Rewrite `NEXT-START-HERE.md` with: "Setup done (ADR-0001). Next: <the owner's first piece of work>."

## Changing it later

The tiers are the owner's to change at any time. Re-run this skill ("redo the ownership tiers") or
edit the table by hand. Either way, the change goes into a new ADR that supersedes 0001. The reason
is written down at the time, not reconstructed later.
