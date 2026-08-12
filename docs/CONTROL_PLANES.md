# Control Planes

The repository follows this separation:

```text
Owner Authority
      |
      v
Policy / Capability
      |
      v
Coordination / Lifecycle
      |
      +------------------+------------------+
      |                  |                  |
      v                  v                  v
Runtime Core      Integration Plane   Documentation
      |                  |                  |
      v                  v                  v
Execution         CI / Evidence       Decisions
      \                  /
       v                v
             SCAR / Verified Evidence
                       |
                       v
                   Promotion
```

## Runtime core

Production bridges, cryptography, local execution, self-fixer behavior, and device/runtime adapters.

## Integration plane

Dashboards, ownership checks, CI workflows, transport adapters, and evidence generation. The integration plane must not silently become an authority source.

## Coordination and lifecycle

Branches, leases, promotion gates, routing, and owner-controlled integration actions.

## Documentation

Architecture contracts, decisions, runbooks, threat models, and current-state records.

## Evidence rule

A label, connector, dashboard claim, or static file is not proof of active capability. Promotion requires a reproducible validation result and, where applicable, signed evidence.
