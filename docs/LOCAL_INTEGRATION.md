# Local Integration Guide

This repository is the application and dashboard layer for the local Sovereignty workspace. It integrates with sibling checkouts without importing their private state or granting provider authority.

## Repository roles

| Repository | Role | Required at startup |
|---|---|---:|
| `Appel420/DevAssist420` | Device-facing assistant/application shell | Optional client |
| `Appel420/Sovereignty-AI-Studio` | Dashboard, bridges, workspace integration | Yes |
| `Appel420/Sovereignty-AI-Gate` | Root Authority, identity, policy, evidence boundary | Yes |
| `Appel420/Sovereignty-Risk-Engine-Runtime-Assurance` | Runtime assurance and risk checks | Yes |
| `Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton` | Informative/reference application skeleton | Optional |

The Studio repository remains the integration host. The Gate and Risk Engine are local sibling services or libraries. The skeleton is never treated as an authority source.

## Local workspace

```text
~/Sovereignty/
├── DevAssist420/
├── Sovereignty-AI-Studio/
├── Sovereignty-AI-Gate/
├── Sovereignty-Risk-Engine-Runtime-Assurance/
└── SuperGrok-Heavy-4-2-Skeleton/
```

Set `SOVEREIGNTY_WORKSPACE` to use another location.

## Startup order

```text
Canonical state
  → Sovereignty-AI-Gate
  → Risk Engine Runtime Assurance
  → Studio local bridges and dashboard
  → DevAssist420 client
```

If the Gate or Risk Engine is unavailable, the launcher must not start provider adapters, credential consumers, or external network clients. Local diagnostics remain available.

## Setup

From this repository checkout:

```bash
./scripts/setup-local-integration.sh
```

The script clones only repositories that are missing, never overwrites an existing checkout, and does not create credentials or start services.

## Preflight

```bash
python3 scripts/local_integration.py check
```

The preflight checks repository presence, Git metadata, required local files, and configured loopback endpoints. It does not call remote providers.

## Start

```bash
./scripts/start-local-integration.sh
```

The launcher performs a fail-closed preflight, then starts only the Studio's existing local launcher when present. It does not start Docker, remote providers, or cloud agents automatically.

## Boundaries

- Credentials remain in the device keystore or local vault.
- Repository checkouts contain source code, not canonical authority or private memory.
- Provider folder names do not grant permission.
- The dashboard reads local cache and does not call providers directly.
- `SCARLedger` records policy-relevant local integration decisions.
- The sibling repositories are pinned by local path and optional commit, not copied into the Studio runtime.

## Diagnostics

The integration manifest is `integration/local-repositories.json`. It is declarative metadata only; it contains no credentials or private state.
