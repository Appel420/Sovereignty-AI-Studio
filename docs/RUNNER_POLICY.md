# CI Runner Policy (Owner Authority)

**Status:** LOCKED  
**Branch authority:** owner-controlled first-party workflows  
**Judge / executioner:** Human owner

## Required execution model

First-party CI is **hybrid and portable**. Workflows run on a broadly available hosted runner by default and support sovereign self-hosted execution when the repository variable `SOVEREIGN_CI_RUNNER` is configured.

Portable jobs use:

```yaml
runs-on: ${{ vars.SOVEREIGN_CI_RUNNER || 'ubuntu-latest' }}
```

Supported sovereign value:

```text
self-hosted Linux arm64
```

Default hosted value:

```text
ubuntu-latest
```

macOS workflows may use `macos-latest` or `macos-15` when native Apple/Xcode tooling is required.

## Enforcement

The canonical policy checker is:

```bash
python3 scripts/check-runner-policy-hybrid.py
```

It accepts only the portable hybrid expression, the canonical sovereign ARM64 runner, `ubuntu-latest`, and native macOS runners. Unknown runner declarations fail closed.

## Why this model

The previous policy prohibited GitHub-hosted runners while Python CI requested `ubuntu-latest`. That was internally contradictory. The hybrid model removes that contradiction without binding CI to one physical host, network, or device.

GitHub Actions selects a runner before a job starts. Therefore automatic in-job fallback is not used. The default hosted path provides broad availability; an operator can explicitly select a registered sovereign ARM64 runner through `SOVEREIGN_CI_RUNNER`.

## Global portability boundary

Portability does not mean every arbitrary device can execute GitHub Actions directly. Device-local and offline execution belongs to the repository's local CI path. Remote CI has two supported execution classes: GitHub-hosted runners and sovereign self-hosted runners.

## Scope

This policy applies to all first-party `.github/workflows/*.yml` and `.yaml` files. Vendored `external/` content is outside first-party runner enforcement.
