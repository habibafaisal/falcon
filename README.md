# Falcon

A Claude Code harness for codebases where a silent bug costs money: payments, ledgers, lending,
anything audited.

Extracted from building a live money-movement platform with Claude Code. It assumes you already use
general practices (spec, plan, test-first, worktrees, code review) and adds what those don't catch:

1. **Risk-tiered ownership.** Work is tiered by what a silent bug would cost. Money, identity, and audit
   code is UNDERSTAND-IT: the human hears the design one concept at a time and ratifies it.
2. **Graded evidence, independent review.** Nothing is "done". The builder never verifies its own work,
   and a test only counts once it's been seen failing with its guard broken.
3. **Misses become checks.** Every miss a human catches becomes an escape record plus an enforced check
   in the same session, not a note.
4. **A guard ladder.** Rules that get broken move from prose to failing checks to hooks that block.

Read [`METHOD.md`](METHOD.md) for the loops, and [`examples/case-studies/`](examples/case-studies/) for six
real misses that produced checks.

## What's in the box

```
template/                         → copied into your repo by install.sh
  CLAUDE.md                       working agreement: ownership tiers, review layer, guidelines
  NEXT-START-HERE.md, NEXT.md     session handoff + never-lossy to-do
  INVARIANTS.md, ARCHITECTURE.md  the law and the map
  docs/working_rules.md           W1–W12 process rules
  docs/mistakes.md                recurring-mistake log (seeded with 8 common classes)
  docs/adr/                       decision records
  .claude/settings.json           wires the hooks
  .claude/hooks/                  protect_paths · no_stash_while_live · next_md_size
  .claude/protected_paths.txt     the delegation fence's path list
  .claude/agents/oracle.md        read-only codebase oracle
  .claude/skills/review-harness/  init · review · sweep · escape
  review/                         GATES · SCENARIOS · HAZARDS · verify.py · falcon.toml
examples/case-studies/            sanitized escapes
tests/                            tests for verify.py and the hooks
```

## Install

```bash
git clone https://github.com/habibafaisal/falcon.git
./falcon/install.sh /path/to/your/repo     # never overwrites; lists files to merge by hand
```

Then:
1. Fill in `CLAUDE.md` and adapt the ownership table to your domain.
2. List your money, identity, and audit paths in `.claude/protected_paths.txt`, each with what a delegate
   could silently break there.
3. Set `source_dir` and `test_command` in `review/falcon.toml`, and name your source of truth in
   `review/GATES.md`.
4. `pip install pyyaml` (plus `tomli` on Python < 3.11).

## Daily use

| When | Do |
|---|---|
| Orienting | Ask the `oracle` agent before reading files |
| Before money/identity work | Walk the design with the owner and record an ADR |
| After building | `python review/verify.py <slug>`, then "review this capability" (fresh agent) |
| Before promoting a capability | "sweep <slug>": prove the tests go red under mutation |
| Owner catches a miss | "record an escape", then add the new check in the same session |
| End of session | Rewrite `NEXT-START-HERE.md` and update `NEXT.md` |

## Develop

```bash
uv run --with pytest --with pyyaml pytest
```
