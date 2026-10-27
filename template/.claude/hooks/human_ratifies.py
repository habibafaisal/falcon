#!/usr/bin/env python3
"""PreToolUse guard — only the owner ratifies a plan.

`review/verify.py --plans` lets UNDERSTAND-IT code through only when a plan in docs/plans/ says
`status: ratified`. If an agent could write that line, the gate would check nothing. So this hook
denies ANY agent write (main session included, unlike the delegation fence) that would put
`status: ratified` into a plan:
  - Edit / MultiEdit whose new text sets it and whose old text didn't have it,
  - Write of a plan file whose content has it (rewriting a ratified plan needs re-ratifying),
  - a Bash command that names docs/plans and contains `status: ratified` (sed, tee, echo >>, ...).

The owner ratifies by editing the file themselves, or with a `!` command (that bypasses hooks).

Limits: an Edit that changes other lines of an already-ratified plan is allowed (only the status
line is guarded), and the Bash check is textual. It closes the easy path, not every path; the
plan's git history still shows who changed what.

Fail-open (same as the other hooks): unparseable payload ⇒ allow. Deny mechanism:
`hookSpecificOutput.permissionDecision: "deny"` on stdout at exit 0.
"""
import json
import os
import re
import sys

_RATIFIED = re.compile(r"^\s*status:\s*['\"]?ratified\b", re.IGNORECASE | re.MULTILINE)
_RATIFIED_ANYWHERE = re.compile(r"status:\s*['\"]?ratified\b", re.IGNORECASE)
_PLANS = "docs/plans/"


def _is_plan(file_path: str, root: str) -> bool:
    abs_path = os.path.normpath(file_path if os.path.isabs(file_path) else os.path.join(root, file_path))
    rel = os.path.relpath(abs_path, os.path.normpath(root)).replace(os.sep, "/")
    return rel.startswith(_PLANS) and rel.endswith(".md") and "/0000-" not in "/" + rel


def ratifies(payload: dict, root: str) -> bool:
    tool, ti = payload.get("tool_name"), payload.get("tool_input") or {}
    if tool == "Bash":
        cmd = ti.get("command", "")
        return _PLANS in cmd and bool(_RATIFIED_ANYWHERE.search(cmd))
    if not _is_plan(str(ti.get("file_path") or ""), root):
        return False
    if tool == "Write":
        return bool(_RATIFIED.search(ti.get("content", "")))
    edits = ti.get("edits") if tool == "MultiEdit" else [ti]
    return any(_RATIFIED.search(e.get("new_string", "")) and not _RATIFIED.search(e.get("old_string", ""))
               for e in edits or [])


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = os.environ.get("CLAUDE_PROJECT_DIR") or str(payload.get("cwd") or os.getcwd())
        deny = ratifies(payload, root)
    except Exception:  # noqa: BLE001 — fail-open, see docstring
        return 0
    if not deny:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Refused: only the owner sets a plan to `status: ratified`. Leave it `proposed`, walk the "
                "owner through the plan, and let them ratify it by editing the file themselves."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
