# SGHv119 PHPWin and three-mode status contract

This document defines the SGHv119 documentation surface for the PHPWin/iOS
local node. The dashboard is a read-only projection; it does not authorize,
route, mutate, or grant access.

## Runtime flow

```text
Human Owner
  -> Policy / Capability Decision
  -> GateOne
  -> Runtime Mode Resolution
  -> SGHv119 Routing
  -> DevAssist420 Execution
  -> ExecutionReceipt
  -> SCAR / AUDIT / REPMHL Evidence
  -> Read-only Dashboard
```

## Three modes

```text
LOCAL
  -> loopback-only
  -> device-local state
  -> no external memory
  -> no automatic network fallback

HYBRID
  -> device-local state remains authoritative
  -> scoped approved external operation
  -> visible destination and scope

ONLINE
  -> explicit owner selection required
  -> visible destination and transferred fields
  -> audit and revocation required
```

Allowed transitions:

```text
LOCAL failure + owner approval -> HYBRID
HYBRID + explicit owner selection -> ONLINE
ONLINE operation complete -> LOCAL
LOCAL -> ONLINE                         FORBIDDEN
HYBRID -> ONLINE without approval        FORBIDDEN
```

## PHPWin endpoints

The PHPWin/iOS local package exposes these loopback endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Local health and active mode |
| `GET` | `/api/status` | Mode, OAuth, network, and audit status |
| `POST` | `/api/event` | Emit a local event and record evidence |
| `GET` | `/diagnostics/phpinfo.php` | Protected diagnostics only |

The diagnostics endpoint is disabled by default. When explicitly enabled it
requires both loopback access and:

```text
X-Sovereignty-Diagnostics: OWNER_LOCAL_ONLY
```

## Artifact classes

```yaml
artifact_classes:
  canonical:
    authority: true
    examples:
      - policy manifests
      - identity records
      - trust anchors
      - SCAR ledger
  derived:
    authority: false
    examples:
      - dashboard projections
      - caches
      - reports
  external:
    authority: false
    examples:
      - Git mirrors
      - provider metadata
      - imported files
```

A dashboard projection is never runtime truth. A GitHub repository listing is
never authorization. A provider adapter is never a policy authority.

## Verification

Run locally from the dedicated branch:

```bash
python3 -m pytest -q tests/test_readme_governance.py
python3 scripts/validate-php-ios-environment.py
```
