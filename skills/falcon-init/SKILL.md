---
name: falcon-init
description: Install the Falcon harness into the current repo from the local Falcon clone, then run its setup interview. Use when the owner says "set up falcon", "install falcon", "falcon init", or "start this project with falcon".
---

# Falcon init

Installs Falcon into the repo you're in, then hands off to that repo's `falcon-setup` interview.
This skill only copies files. **Every choice about the project is made in `falcon-setup`, by the owner.**

## Step 1 — Check the target

1. Find the repo root: `git rev-parse --show-toplevel`.
   - Not a git repo? Ask the owner whether to `git init` here. Don't do it without a yes.
2. Already installed? If `CLAUDE.md` exists **and** has no `<Project>` placeholder, and
   `.claude/skills/falcon-setup/` exists, say so and stop. To redo the tiers, use `falcon-setup`
   ("redo the ownership tiers").
3. Uncommitted changes? Mention it, so the owner can tell Falcon's files apart from their own.

## Step 2 — Find Falcon

Look for the Falcon clone in this order: `$FALCON_HOME`, then `~/falcon`. If neither has `install.sh`,
ask the owner where their clone is. If they have none, offer to run
`git clone https://github.com/habibafaisal/falcon.git ~/falcon`, and run it only on a yes. Never pull
or update the clone on your own.

Show which version is about to be installed: `git -C <falcon> log -1 --oneline`, plus
`git -C <falcon> status --short`. If there are uncommitted changes, say that they will be installed too.

## Step 3 — Install

Run `<falcon>/install.sh <repo-root>`. It never overwrites a file.

If it lists **skipped** files (they already exist in the repo, e.g. an existing `CLAUDE.md`): don't
merge them yourself. Show the list and ask the owner, file by file, whether to merge Falcon's version
in by hand now or leave it.

## Step 4 — Hand off to setup

Run the repo's `falcon-setup` skill. If it isn't available in this session yet (the skill was copied
in after the session started), read `<repo-root>/.claude/skills/falcon-setup/SKILL.md` and follow it
directly.

## Step 5 — Close

After setup finishes, list what was installed and what was filled. Suggest one commit with exactly
Falcon's files and the setup output (commit by path). Commit only on the owner's yes.
