# CI naming and router mode

## Convention

```text
<test-domain>-<test-scope>-ci-<mode>
```

| Mode | Meaning |
|------|--------|
| **local** | Device/offline only; no external calls |
| **hybrid** | Local + approved services; owner approval |
| **online** | Hosted/live; owner approval + full audit |

Mode must appear in the **CI name**, console header, report JSON, and SCAR route metadata.

## Ara / this lane

```text
CI:   ara-hardened-unit-ci-local
MODE: LOCAL
ROUTE: offline-safe
```

Workflow: `.github/workflows/ara-hardened-ci.yml`  
Local runner: `python scripts/run-local-ci.py --ci-name ara-hardened-unit-ci-local`

## Router rule

```text
uncertain → local
sensitive data → local
no owner approval for hybrid/online → local
```

```text
router decides where (local | hybrid | online)
policy decides whether
QuadRatchet protects data
SCAR records what happened (not private content)
owner controls escalation
```

## Per-branch defaults

See `config/ci-mode-registry.json`.

Each agent lane should register its own `…-unit-ci-local` name. Hybrid/online names exist only as **authorized** escalations, not silent defaults.
