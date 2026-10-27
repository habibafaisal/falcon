#!/usr/bin/env python3
"""Stop hook — a SOFT, non-blocking size warning for NEXT.md.

NEXT.md is the session-continuity source of truth; left unmanaged it grows append-only
(on the project this was extracted from it reached ~80k tokens before a cap). This hook nudges toward
collapsing superseded narrative into the `git log -p NEXT.md` pointer when the file drifts
back over budget. It is deliberately a SOFT warn (the owner's call): it can only ever exit 0
and NEVER blocks a Stop — a hard cap would fight the operator exactly when they are
legitimately appending pick-up state mid-session. The warning rides in `systemMessage`;
if a harness build doesn't render that field the hook harmlessly no-ops.

Budget is a rough char/4 token estimate — precise tokenization isn't worth the dependency
for a nudge. Fail-open on ANY error: a broken size-nudge must never interfere with stopping.
"""
import json
import os
import sys

BUDGET_TOKENS = 12_000  # ~48KB; over this, collapse history to git


def main() -> int:
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        path = os.path.join(root, "NEXT.md")
        if not os.path.exists(path):
            return 0
        with open(path, encoding="utf-8") as fh:
            chars = len(fh.read())
        tokens = chars // 4
        if tokens > BUDGET_TOKENS:
            over = tokens - BUDGET_TOKENS
            msg = (
                f"NEXT.md is ~{tokens:,} tokens (budget {BUDGET_TOKENS:,}; ~{over:,} over). "
                "Collapse superseded/dated session narrative into the "
                "'Session history (collapsed — full narrative in `git log -p NEXT.md`)' "
                "pointer — the blow-by-blow is already preserved in git. Keep only durable "
                "current state (pick-up queue, durable decisions, open questions)."
            )
            print(json.dumps({"systemMessage": msg}))
        return 0
    except Exception:  # noqa: BLE001 — a size nudge must never block stopping (fail-open)
        return 0


if __name__ == "__main__":
    sys.exit(main())
