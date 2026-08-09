# Commit 23 — Principal Authority Boundary

The Rust workspace mechanically separates:

```text
principal      -> describes identity, capabilities, and network boundary
policy-engine  -> owns authorization decisions
orchestrator  -> routes an existing decision only
```

The following invariants are enforced by API shape and tests:

- no `GrantCapability`, `OverridePolicy`, or `ModifyLedger` capability exists;
- external access requires `NetworkBoundary::AuthorizedExternal`;
- the orchestrator receives a decision and cannot authorize a principal;
- transport, evidence, storage, and ledger layers are not dependencies of the orchestrator;
- human approval remains a distinct decision state.

This commit does not add TLS roots, dashboards, evidence storage, council logic,
or deployment profiles. Those belong to later bounded commits.
