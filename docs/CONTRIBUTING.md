# Contributing to Sovereignty AI

## Local-first execution rule

All development and validation must default to the self-hosted Linux runner or a device-local checkout. Do not route repository work through cloud coding agents, hosted runners, SaaS scanners, remote providers, CDNs, or cloud artifact services.

External services are opt-in only, require explicit owner approval and policy authorization, and must never be required for local startup, tests, dashboard operation, cached data, or diagnostics.

## Implementation rules

- Preserve the human owner as the only Root Authority.
- Keep the default decision `DENY`.
- Keep `SG_NETWORK_MODE=offline` for local validation unless an owner-approved test explicitly requires another mode.
- Bind local services to loopback: Python `9897`, dashboard `9898`, Node `9899`.
- Keep private data, credentials, reasoning text, and evidence local by default.
- Do not initialize providers, remote clients, polling loops, WebSockets, SSE streams, or credential consumers before `PolicyEngine` succeeds.
- Do not add mandatory cloud services or remote UI/CDN dependencies.
- Treat instructional patch files as documentation unless they are complete runtime modules.

## Validation

Run these commands on the self-hosted Linux runner:

```bash
bash -n START_SERVER.sh start-all.sh scripts/local-ci.sh
python3 -m compileall -q --exclude external --exclude .venv .
flake8 --count --select=E9,F63,F7,F82 --show-source --statistics
node --check node-bridge/server.js
bash scripts/local-ci.sh
```

A missing optional external tool is not a reason to switch to a cloud runner. Add a local implementation or mark the optional capability unavailable while preserving safe local operation.
