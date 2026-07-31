# SGHv119 — Local Status Panel

**Branch:** ara-hardened  
**Endpoint:** `GET http://127.0.0.1:9898/api/local-status`  
**Source:** `bridge/serve_dashboard.py` → `bridge/local_dashboard_status.py`

## Response shape

```json
{
  "mode": "offline",
  "network_access": false,
  "external_oauth": "disabled",
  "oauth_policy": true,
  "oauth_generator": true,
  "local_state_validator": true,
  "local_ci": true,
  "approvals": true,
  "issue_suggestions": true,
  "m4_neural": {
    "available": true,
    "path": "docs/apple_m4_neural.md",
    "tops": 38,
    "memory": "unified",
    "href": "docs/apple_m4_neural.md"
  }
}
```

## Dashboard panel (read-only)

| Row | Source field |
|-----|----------------|
| Mode | `mode` + `network_access` |
| External OAuth | `external_oauth` |
| OAuth policy / generator | `oauth_policy`, `oauth_generator` |
| Local CI | `local_ci` |
| Local-state validator | `local_state_validator` |
| Approvals / issue suggestions | `approvals`, `issue_suggestions` |
| Apple M4 Neural Engine | `m4_neural.tops` (38), `m4_neural.memory` (unified) |
| Doc link | `m4_neural.href` |

## Minimal fetch for SGHv119.html

```javascript
async function refreshLocalStatus() {
  try {
    const r = await fetch('http://127.0.0.1:9898/api/local-status', { cache: 'no-store' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    // render: Mode, OAuth, Local CI, State, M4 38 TOPS unified
    return d;
  } catch (e) {
    return { mode: 'offline', network_access: false, error: String(e), m4_neural: { tops: 38, memory: 'unified', available: false } };
  }
}
```

Fail closed: if the endpoint is unreachable, show offline + M4 doc missing — never invent online or cloud OAuth.

## Local CI gate

```bash
python3 scripts/validate-local-dashboard.py
pytest -q tests/test_local_status.py
```
