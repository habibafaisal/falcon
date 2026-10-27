# GATES — states, permitted uses, promotions, human checkpoints

A verdict never says "done": it states both axes and what blocks promotion.

## Vocabulary

**capability_state** (how far it has actually been taken):

| State | Meaning |
|---|---|
| not_started | nothing beyond intent |
| implemented | code exists, unit-level evidence only |
| integrated | wired into the real call path |
| exercised | run end-to-end on real or representative data |
| validated | evidence graded, scenarios covered, verdict written |
| operational | running in its permitted use, watchable and recoverable |

**permitted_use** (what the output may cause):

| Use | Meaning |
|---|---|
| prototype_only | throwaway; output allows nothing |
| demo_only | may be shown; never fed downstream |
| historical_backtest | may run over frozen historical data |
| shadow_mode | runs beside the live system; output compared, never acted on |
| human_approved_live | acts on reality only after a named human approves each action |
| automated_live | acts on reality without per-action approval |

## Promotion requirements

Data the verifier reads, not script logic. Fill in per repo.

| Promotion | Requires |
|---|---|
| implemented → integrated | <e.g. wired into the real entry point; governing tests exist> |
| integrated → exercised | <e.g. end-to-end run on representative data, evidence path recorded> |
| exercised → validated | <e.g. scenarios demonstrated; evidence_class ≤ N; executed: true> |
| validated → operational | <e.g. kill switch + recovery shown; open hazards accepted by a human> |
| any → higher permitted_use | <e.g. human checkpoint recorded; blocking hazards resolved> |

## Human checkpoints

These attach to **decision types, not files**. Each needs an explicit, recorded human decision:

- critical formula (anything that changes an amount, dose, score, or other decided-on value)
- workflow state transition (what states a record may move between)
- promotion on either axis
- tenant boundary
- which document/system wins on conflict
- irreversible external action (emails, payments, filings, deletions, deploys)
- accepting an open hazard

## Intent sources

Per repo. Review files **cite** these, never copy them.

- Executable contract: `<path>`
- Overrides on meaning/economics: `<path or "none">`
- Human decision log: `<path>`
