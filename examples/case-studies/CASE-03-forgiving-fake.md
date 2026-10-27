# CASE-03 — The forgiving fake

**Class:** architectural-boundary · external contract. **Caught by:** the owner, on a live sandbox run.

## What happened
User provisioning called an identity provider's "create user" API. The provider requires a password
field for this connection type; the request omitted it. **14 tests passed.** The first live call
returned `400 "password" is required`.

A sibling miss on the payment rail: a `Decimal` amount the real HTTP client couldn't serialize — the
fake accepted it.

## Why every layer missed it
- Every test replaced the whole client with a fake that asserted orchestration ("we called
  create_user") and never looked at the request body. The wire contract was untested by construction.
- "It passed" meant "our fake accepted our call", not "the provider would."

## The check that exists now
- A test that drives the **real** client through a mocked HTTP transport, captures the posted JSON,
  and asserts the password is present and policy-compliant. Verified red by removing the field.
- **SCENARIOS P3** and **HAZARDS H7:** every wholesale fake needs a real-wire sibling test.

**Lesson:** a fake is a claim about the vendor; test the claim.
