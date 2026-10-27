#!/usr/bin/env python3
"""PreToolUse guard — a DELEGATED subagent may not write UNDERSTAND-IT code.

The working agreement (CLAUDE.md) marks a trigger set as UNDERSTAND-IT: code where a silent bug moves
money wrongly, merges two real identities, forges the audit trail, or breaks determinism. That code is
built WITH the owner's understanding, never silently by a delegate. This hook makes the prose rule
MECHANICAL: a subagent's Write/Edit to a protected path is denied at the tool boundary; the main
session (the owner's own work) is never touched.

Main vs subagent: the PreToolUse payload carries `agent_id` ONLY when the call originates inside a
subagent. No `agent_id` => main session => always allow. Zero friction for the owner's own work.

Protected paths live in `.claude/protected_paths.txt`, one per line, each with its NAMED INVALIDATION
as a trailing comment. A trailing "/" protects a directory prefix; otherwise an exact file. The
inclusion test is not "this path is important" — it is: could a delegate editing this path change
MONEY CORRECTNESS, IDENTITY, AUDIT TRUTH, DETERMINISM, or the CERTIFICATION BOUNDARY? If you can't name
the invalidation, the path doesn't belong (otherwise the fence creeps and starves delegated work).

Turning it off: set `FALCON_FENCE=off` in the environment, or empty the paths file. Record WHY in
docs/working_rules.md — a fence switched off silently is worse than none.

Fail-open (deliberate, scoped): unparseable payload or no file_path => ALLOW. It denies only when it can
POSITIVELY identify (subagent AND protected path). Blocking on a parse error would break every write in
the session. The fence is a delegation guard, not the last line of defence — tests, DB constraints and
the review harness remain the backstops.

Deny mechanism: `hookSpecificOutput.permissionDecision: "deny"` on stdout at exit 0. Exit 2 would block
but DISCARD the reason, so it is never used.
"""
import json
import os
import sys

PATHS_FILE = os.path.join(".claude", "protected_paths.txt")


def load_protected(root: str) -> tuple[str, ...]:
    """Entries from the paths file: text before any '#', blank lines skipped."""
    try:
        with open(os.path.join(root, PATHS_FILE), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return ()
    entries = (line.split("#", 1)[0].strip() for line in lines)
    return tuple(e for e in entries if e)


def _repo_relative(file_path: str, root: str) -> str | None:
    """`file_path` relative to the repo root, or None if it escapes the repo."""
    if not file_path:
        return None
    abs_path = os.path.normpath(file_path if os.path.isabs(file_path) else os.path.join(root, file_path))
    try:
        rel = os.path.relpath(abs_path, os.path.normpath(root))
    except ValueError:  # different drive on Windows — outside
        return None
    if rel.startswith(".."):
        return None
    return rel.replace(os.sep, "/")


def is_protected(rel: str, protected: tuple[str, ...]) -> bool:
    for entry in protected:
        if entry.endswith("/"):
            if rel == entry.rstrip("/") or rel.startswith(entry):
                return True
        elif rel == entry:
            return True
    return False


def decide(payload: dict, root: str) -> tuple[bool, str]:
    """(deny?, relpath). Deny only when POSITIVELY (subagent AND protected path)."""
    if os.environ.get("FALCON_FENCE", "").lower() == "off":
        return False, ""
    if "agent_id" not in payload:  # main session — never fenced
        return False, ""
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    rel = _repo_relative(str(file_path), root)
    if rel is None:
        return False, ""
    return is_protected(rel, load_protected(root)), rel


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — a broken payload must not block the session (fail-open)
        return 0
    if not isinstance(payload, dict):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or str(payload.get("cwd") or os.getcwd())
    deny, rel = decide(payload, root)
    if not deny:
        return 0
    agent = payload.get("agent_type") or payload.get("agent_id") or "a delegated subagent"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"BLOCKED: {agent} may not write `{rel}`. This path is UNDERSTAND-IT (see "
                ".claude/protected_paths.txt for its named invalidation). Delegates STUB these, they do "
                "not BUILD them. Return the proposed change to the main session for the owner to review "
                "and apply."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
