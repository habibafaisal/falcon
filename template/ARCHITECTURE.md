# ARCHITECTURE — the map

Kept current in the same change as the code (`python review/verify.py --map` fails on dead paths and
undocumented packages). The `oracle` agent reads this; humans skim it.

## Packages

Mark UNDERSTAND-IT packages with 🔵 — they should match `.claude/protected_paths.txt`.

| Package | Responsibility | Tier |
|---|---|---|
| `app/<pkg>/` | <one line> | delegate / 🔵 |

## Flows

<The two or three paths critical data takes through the system, step by step.>

## Things that must stay in sync (the drift checklist)

1. <e.g. a new effect on the webhook ⇒ the same effect on the scheduled sweep (SCENARIOS P4)>
