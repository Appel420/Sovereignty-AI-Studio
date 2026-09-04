# Local coordination wiring

`LocalCoordinationSpine` is the integration point between the existing local
components. It connects:

```text
AgentMessage
   ↓
agent/provider/branch validation
   ↓
ConflictManager scope hold
   ↓
optional injected LeaseIssuer verification
   ↓
LocalAgentBus delivery or local queue
   ↓
ExecutionReceipt
   ↓
EvidenceAdapter → SCAR/REPMHL sinks
```

The spine does not mint authority, select providers, modify repositories, or use
network services. A state-changing operation must provide an already-issued lease
and remain subject to the owner approval and capability gates outside this module.

Communication uses the local bus. An unregistered recipient is queued in the local
bus object; a production adapter may persist that queue under the owner-approved
Unix socket or local encrypted store. `Collaboration`, `main`, and promotion remain
owner-controlled.
