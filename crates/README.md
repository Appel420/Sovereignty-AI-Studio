# Commit 23 — Principal Authority Boundary

This workspace separates principal description, policy authorization, and task routing.

- `principal` describes identities, capabilities, and network boundaries.
- `policy-engine` is the only authorization decision-maker.
- `orchestrator` routes an existing decision and cannot grant authority.

The dashboard, evidence, transport, and ledger layers are intentionally outside
this bounded commit.
