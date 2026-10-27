# CASE-01 — Tests agreed with wrong code

**Class:** product-meaning · money. **Caught by:** the owner, reading the result.

## What happened
On a short payment (the payer sends less than owed), two parties have a claim on what arrives: the
customer's **reserve** and the platform's **fee**. The ruling: the reserve absorbs the shortfall first
— it is the *first-loss* piece — and the fee is *senior*, forgone only once the reserve is exhausted.

The build inverted it: customer paid first, fee from what was left. On an illustrative collection of
92 against face 100 (advance 90, fee 3) it posted **customer 2, fee 0** where the rule gives
**customer 0, fee 2**.

## Why every layer missed it
- **The builder** read one ambiguous sentence in the ruling narrative ("the fee leg is subordinated")
  instead of the formula, which is unambiguous.
- **The fresh reviewer** re-read the same sentence the same way and ratified it. It even noted the
  tests couldn't distinguish the orderings — and stopped there.
- **The tests** were written in the same session as the code; the expected values were the code's own
  output (evidence class 4). And a balanced ledger sums to zero *under either ordering*, so no balance
  check could ever tell them apart.

## The check that exists now
- A regression test written by an independent agent, with values worked out by hand from the
  formula, at inputs (92 and 98) where the two orderings give **different** numbers. It asserts the
  split equals the canonical values *and differs from* the rival ones.
- **SCENARIOS P1 (canonical fixture):** every priority or split rule is pinned this way.

**Lesson:** test-first doesn't help when the same mind writes the spec reading, the test, and the code.
