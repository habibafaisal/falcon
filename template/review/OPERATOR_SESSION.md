# Operator session (Loop 8)

Copy this block into `review/operator-sessions/YYYY-MM-DD-<slug>.md` each time you exercise the system as
a real operator would. Do it after any change on a trigger path, before you call that change done.

Any diff you find here is an escape candidate, so it goes to Loop 6 (`review/escapes/`) and needs a new check.

---

## 1. What changed
- Change / commit under test:
- Trigger path it touches (money · health · auth · data · infra):

## 2. Outside source of truth
The thing the system must agree with, which the system does not control.
Examples: bank or rail statement, provider console, lab result, upstream API's own record.
- Source:
- How you read it (URL, export, CLI):

## 3. Awkward cases to try
Tick what you ran. Add your own and keep the good ones as seeds for the next session.
- [ ] Happy path, one unit (one payment, one record)
- [ ] Reversal / return / cancellation **after** the system thinks it's done
- [ ] Retry or double-click the same action (does it happen twice?)
- [ ] Partial failure halfway through (kill the process or step, then resume)
- [ ] The moment **between** two async steps (webhook arrived, sweep not yet run)
- [ ] Boundary values: zero, smallest unit, a date at a timezone edge
- [ ] Wrong role / wrong tenant tries the action

## 4. Reconcile at the totals level
Compare **totals**, not only rows. A balance that is off by a small amount between two steps is the
classic escape. (Seed from the origin codebase: the ledger read $1 above the bank between the
webhook and the sweep.)

| Quantity | System says | Source of truth says | Diff | Explained? |
|---|---|---|---|---|
| | | | | |

## 5. Optional: let Claude drive the UI
If the operator surface is a web app, Claude Code can drive it through the Claude in Chrome extension.
It clicks through the case list above, records a GIF, and reads the browser console and network log.
**Claude drives. The human still reads the source of truth and signs the diff table.** A
browser-driving agent proves the screen did what was clicked, not that the money or data is right.
- GIF / screenshots:
- Console errors or failed requests seen:

## 6. Outcome
- [ ] No diff: session recorded, done.
- [ ] Diff found: escape `ESC-YYYY-NNN` opened, and the new check that would have caught it is named here:
