# SCENARIOS — standing failure scenarios

Every capability is judged against these. Each relevant one is marked in the capability
file: **demonstrated** (evidence file exists), **inferred** (argued from code),
**contradicted**, or **unverified**.

| id | scenario |
|---|---|
| S1 | **Wrong rule** — code is internally correct but implements the wrong thing. Would the authority quote catch the difference? |
| S2 | **Circular evidence** — the test's expected values came from the code's own output. Would anything fail if the code was wrong from day one? |
| S3 | **Never built** — a needed property (scoping, durable control, lockfile, audit record) simply doesn't exist. What proves it does? |
| S4 | **Computed = allowed** — a calculated value is treated as permission to act. Where is the gate between computing and acting? |
| S5 | **Crash mid-write** — process dies halfway. What state is left; does resume duplicate or lose work? |
| S6 | **Same input twice** — is the effect applied once? |
| S7 | **Boundary crossing** — data or actions leak between tenants/actors/scopes. What stops it, everywhere? |
| S8 | **Silent partial failure** — some items in a batch fail but the batch reports success. How would anyone know which? |
| S9 | **Can't see, can't stop** — it misbehaves in use. Can it be spotted, halted, recovered without losing data? |
| S10 | **Environment drift** — a dependency, schema, or config differs from what was reviewed. Would that be caught before it runs? |
