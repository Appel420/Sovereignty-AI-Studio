# Bridge Routes, Health Aggregation, and AMR Integration

**Branch:** ara-hardened  
**Status:** Implementation contract (ready for code)

## 1. Device State Sovereignty Policy

Formal file: `docs/DEVICE_STATE_SOVEREIGNTY_POLICY_v1.1.1.md`  
Already committed on this branch.

## 2. Bridge routes (to be added)

Target: Python bridge (`bridge.py` / companion HTTP layer on `:9897`) or node-bridge proxy that calls local authority modules.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/policy/check` | Evaluate `state_policy` + provider against Device State Sovereignty Policy. Returns allow / deny + reason. |
| POST | `/ledger/undo` | Body: `{ "entry_id": int, "actor_id": string }`. Append-only undo via UndoableLedger. |
| POST | `/ledger/redo` | Body: `{ "entry_id": int, "actor_id": string }`. Append-only redo. |
| GET | `/ledger/history` | Query: `?target=...`. Return ledger history for a target. |

Rules:
- Fail closed when ledger or authority modules are missing.
- Full reasoning text never leaves the device; only hashes and short summaries.
- Every call produces an audit / SCAR-style evidence record.
- Privileged mutations still require human-owner collaboration gate.

## 3. Health aggregation

Single snapshot consumed by SGHv119 and the terminal. Prefer extending existing node-bridge endpoints:

- `GET /health`
- `GET /api/bridge/status`
- `GET /api/agents/status`

Canonical aggregated shape:

```json
{
  "mode": "device-local",
  "dashboard": "healthy|degraded|offline",
  "pythonBridge": "healthy|degraded|offline",
  "nodeBridge": "healthy|degraded|offline",
  "devassist": "healthy|degraded|offline|not_configured",
  "gate": "healthy|degraded|offline|not_configured",
  "riskEngine": "healthy|degraded|offline|not_configured",
  "amr": "healthy|degraded|offline|not_configured",
  "voice": "healthy|degraded|offline|not_configured",
  "scar": "healthy|degraded|offline|not_configured",
  "network_mode": "offline|hybrid|online",
  "timestamp": "ISO-8601"
}
```

No external discovery. Loopback only unless explicitly configured.

## 4. AMR integration path (provider-neutral)

SGHv119 must treat AMR as a **local registry feed**, not as an opinion source.

- Preferred endpoint: local AMR `GET /api/entities` (or `/api/companies`, `/api/models`, etc.)
- Fallback: load a local verified entities JSON file
- Policy decisions (allow / deny / council membership) live in the **user policy file**, never inside the registry or the terminal hard-coding
- `evidence_score` starts at 0; UI must not invent verification
- Risk fields that have no feed return `null`, not zero

Integration rule for SGHv119:

```
Registry Source
    → Entity Discovery (AMR or local file)
    → User Policy evaluation
    → Route / display decision
    → Evidence record
```

The terminal displays the ecosystem. The user defines the operating policy.

## Implementation order on ara-hardened

1. Policy file (done)
2. Add route stubs + fail-closed handlers that respect the policy
3. Extend health aggregation to the canonical shape above
4. Wire SGHv119 to prefer local AMR `/api/entities` with offline file fallback

No push to `main`. Owner reviews on `ara-hardened`.
