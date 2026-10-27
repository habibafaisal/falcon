# Mistakes — recurring, and the guard that prevents each

A short, durable log of mistakes that **recurred**, why they keep happening, and the check that stops
them. Add an entry the second time a mistake happens; one-offs live in `review/escapes/`.

Read the index, then open only the entries that match the work. The entries below are **seeds** —
mistake classes that recur on most careful codebases. Keep the ones that bite you, delete the rest.

| # | Mistake | Trips when you… |
|---|---|---|
| M1 | Calling already-built work "missing" (the census trap) | claim anything is absent |
| M2 | Right formula, wrong input meaning (semantic substitution) | wire an input to a formula |
| M3 | A dedup key or lock keyed differently from the id it protects | write a unique key, dedup, or row lock |
| M4 | Fixing one of two parallel doors and not its twin | fix a bug in, or add an effect to, a webhook / sweep / retry path |
| M5 | Reverting a probe with `git checkout` deletes the uncommitted build | revert anything |
| M6 | A test fake more forgiving than the real service | test an external call with a fake |
| M7 | Creating an undeletable external resource without a yes and a cleanup plan | create anything on a third-party system |
| M8 | Shipping the build but not the docs that describe it | finish any build |

---

## M1 — The census trap
**Mistake:** a feature looks absent (no obvious handler), so it gets rebuilt — but it existed under
another name, inside another component, or was deliberately deactivated.
**Why it recurs:** trusting a coverage list instead of the code; assuming one rule = one handler.
**Guard:** working_rules W1 — the every-angle check before building or delegating.

## M2 — Semantic input substitution
**Mistake:** the formula is right but an input means something else (e.g. two fields both called
`effective_date`, one meaning "date read", one meaning "invoice date").
**Guard:** when wiring an input, quote the authority's definition of that input next to the field used.

## M3 — Key mismatch
**Mistake:** a dedup guard or row lock keyed on something other than the id it protects, so two writers
both pass the guard.
**Guard:** write down "this key protects <id>"; a test with two concurrent writers on the same id.

## M4 — The twin door
**Mistake:** the same fact arrives by webhook *and* by a scheduled sweep; a fix or new effect lands on
one door only. Recurs one layer up: the twin is a *door*, not a function.
**Guard:** SCENARIOS P4 — parity per effect; grep for every consumer of the event before closing.

## M5 — `git checkout` as undo
**Mistake:** reverting a one-line mutation with `git checkout <file>` reverts the whole file to HEAD,
deleting every uncommitted change in it.
**Guard:** snapshot with `cp` before mutating, restore with `cp`; or commit first. Hook:
`no_stash_while_live.py` blocks stash/checkout/reset while tests or another session are live, and
`no_discard_uncommitted.py` blocks a checkout/restore of any file with uncommitted changes, or
`reset --hard` over them, whatever else is running (CASE-07: the first hook alone let one through).

## M6 — The forgiving fake
**Mistake:** a fake replaces an external client wholesale; tests pass because the fake accepts anything.
Production rejects a missing field, or a `Decimal` the JSON encoder can't serialize.
**Guard:** SCENARIOS P3 — a sibling test through the real client over a mocked transport, asserting the body.

## M7 — Undeletable external resource
**Mistake:** creating an account / number / user on a third-party system that can't be deleted, without
explicit permission or a record.
**Guard:** working_rules W9; log every external resource created with its cleanup path.

## M8 — Docs drift
**Mistake:** code moves, the map doesn't; the next session orients from a stale map.
**Guard:** update `ARCHITECTURE.md` in the same change; `python review/verify.py --map` fails on dead paths.
