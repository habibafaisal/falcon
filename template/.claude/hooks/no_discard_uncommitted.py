#!/usr/bin/env python3
"""PreToolUse guard — no `git checkout/restore <path>` or `git reset --hard` over uncommitted work.

`git checkout -- <file>` looks like a one-line undo. It resets the WHOLE file to the last commit and
silently deletes every uncommitted change in it (examples/case-studies/CASE-06, CASE-07). The sibling
hook no_stash_while_live.py only fires while tests or another session are live, so a revert run right
after the tests finished slipped past it (CASE-07). This hook checks the files themselves: a Bash call
is denied when a checkout/restore names a path with uncommitted tracked changes, or `reset --hard`
runs on a tree that has any.

Follows `cd <dir>` earlier in the same command and `git -C <dir>`. Untracked files don't count: these
commands don't touch them. Switching branches (`git checkout main`, `-b x`) is never blocked: git itself
refuses a switch that would overwrite local changes.

The safe undo for a probe: copy the file before editing it, copy it back after. Or commit first. The
owner can still run the command with the `!` prefix (that bypasses hooks).

Fail-open (same as the other hooks): unparseable payload or a failed git probe ⇒ allow. Deny
mechanism: `hookSpecificOutput.permissionDecision: "deny"` on stdout at exit 0.
"""
import json
import os
import re
import shlex
import subprocess
import sys

_SEGMENT_SPLIT = re.compile(r"&&|\|\||[;&|\n]")


def _dirty(cwd: str, paths: list[str]) -> list[str]:
    """Paths (or files under them) with uncommitted TRACKED changes, staged or not."""
    out = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=cwd,
                         capture_output=True, text=True, timeout=5, check=True).stdout
    return [line[3:] for line in out.splitlines() if line and not line.startswith("??")]


def _discards(tokens: list[str], cwd: str) -> list[str] | None:
    """If this git invocation would discard uncommitted work, the paths at risk; else None."""
    i = 1
    while i < len(tokens) and tokens[i] in ("-C", "-c"):
        if tokens[i] == "-C":
            cwd = os.path.join(cwd, os.path.expanduser(tokens[i + 1]))
        i += 2
    if i >= len(tokens):
        return None
    verb, args = tokens[i], [t for t in tokens[i + 1:] if not re.match(r"^\d*[<>]", t)]
    if verb == "reset":
        return _dirty(cwd, ["."]) or None if "--hard" in args else None
    if verb not in ("checkout", "restore"):
        return None
    if "--" in args:
        paths = args[args.index("--") + 1:]
    elif verb == "restore":
        paths = [a for a in args if not a.startswith("-")]
    else:  # checkout without "--": only arguments that exist on disk are paths; the rest are refs
        if any(a in ("-b", "-B", "--orphan") for a in args):
            return None
        paths = [a for a in args if not a.startswith("-") and os.path.exists(os.path.join(cwd, a))]
    return (_dirty(cwd, paths) or None) if paths else None


def at_risk(command: str, cwd: str) -> list[str] | None:
    for segment in _SEGMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            cwd = os.path.join(cwd, os.path.expanduser(tokens[1]))
        elif tokens[0] == "git":
            risk = _discards(tokens, cwd)
            if risk:
                return risk
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        risk = at_risk(command, cwd)
    except Exception:  # noqa: BLE001 — fail-open, see docstring
        return 0
    if not risk:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Refused: this would discard uncommitted changes in " + ", ".join(risk[:5])
                + (" …" if len(risk) > 5 else "") + ". To undo a probe, restore the file from a copy made "
                "before the edit (`cp`), or commit first. The owner can run it with `!` if it's intended."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
