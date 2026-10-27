#!/usr/bin/env python3
"""PreToolUse guard — no `git stash` / `git checkout` / `git reset` while work is live.

A stash/checkout can yank files out from under a running pytest or a parallel session's uncommitted
edits (examples/case-studies/CASE-06). A prose rule ("never stash/checkout while another session is
live") did not stop it, so this makes it MECHANICAL (the guard ladder, docs/working_rules.md W10): a Bash call running one of those git verbs is
denied when EITHER
  - a pytest process is running, OR
  - another `claude` process has this repo as its working directory (a parallel session).
"Another" = not this session's own `claude` ancestor process.

Allowed always: read-only `git stash list` / `git stash show`. The owner can still run the command
themselves with the `!` prefix (that bypasses hooks) once she has checked nothing is live.

Fail-open (same as protect_paths.py): unparseable payload or a failed process probe ⇒ allow. Deny
mechanism: `hookSpecificOutput.permissionDecision: "deny"` on stdout at exit 0 (exit 2 drops the reason).
"""
import json
import os
import re
import subprocess
import sys

# `git` only at a command position (start, or after ; & | ( or a newline) — so a commit message or
# echo that merely MENTIONS "git stash" is not a match. Quoted text is blanked first for the same reason.
_GIT_VERB = re.compile(
    r"(?:^|[;&|(\n])\s*git\s+(?:-C\s+\S+\s+|-c\s+\S+\s+)*(stash|checkout|reset)\b(\s+\S+)?"
)
_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
_READ_ONLY_STASH = {"list", "show"}


def _risky_verb(command: str) -> str | None:
    for m in _GIT_VERB.finditer(_QUOTED.sub("''", command)):
        verb, nxt = m.group(1), (m.group(2) or "").strip()
        if verb == "stash" and nxt in _READ_ONLY_STASH:
            continue
        return verb
    return None


def _run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=5).stdout


def _own_ancestors() -> set[int]:
    pids, pid = set(), os.getpid()
    while pid > 1:
        pids.add(pid)
        out = _run(["ps", "-o", "ppid=", "-p", str(pid)]).strip()
        if not out:
            break
        pid = int(out)
    return pids


def _live_reasons(project_dir: str) -> list[str]:
    reasons = []
    pytest = [p for p in _run(["pgrep", "-f", "pytest"]).split() if int(p) != os.getpid()]
    if pytest:
        reasons.append(f"pytest is running (pid {', '.join(pytest)})")
    mine = _own_ancestors()
    for p in _run(["pgrep", "-x", "claude"]).split():
        if int(p) in mine:
            continue
        cwd = _run(["lsof", "-a", "-d", "cwd", "-p", p, "-Fn"])
        if any(line == "n" + project_dir for line in cwd.splitlines()):
            reasons.append(f"another Claude session is live in this repo (pid {p})")
    return reasons


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        verb = _risky_verb(command)
        if verb is None:
            return 0
        project_dir = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd", ""))
        reasons = _live_reasons(project_dir)
    except Exception:
        return 0  # fail-open, see docstring
    if not reasons:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"`git {verb}` refused: " + "; ".join(reasons) + ". It can move files out from "
                "under live work. Wait for it to finish, or ask the owner to run it with `!`."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
