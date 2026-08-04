# v0.1 execution boundary note

The repository already contains the narrow DevAssist execution boundary in
`backend/coordination/devassist_adapter.py`.

It accepts only an approved `RouteDecision`, executes an injected local
executor, and returns an `ExecutionReceipt`. It does not authorize, route,
escalate, write branches, or own SCAR/REPMHL. Evidence remains downstream in
`EvidenceAdapter`.

The public v0.1 contract uses the existing names:

```text
RouteDecision.route
RouteDecision.task_id
ExecutionReceipt.task_id
ExecutionReceipt.status
```

The older proposed names `route_type`, `request_id`, and `result` are not
introduced because they would change the frozen public contracts.
