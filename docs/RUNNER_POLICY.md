# CI Runner Policy (Owner Authority)

**Status:** LOCKED
**Branch authority:** owner-controlled first-party workflows
**Judge / executioner:** Human owner

## Required execution model

First-party CI is **hybrid and portable**. Workflows must run on a broadly available hosted runner by default and must support sovereign self-hosted execution when the repository variable `SOVEREIGN_CI_RUNNER` is configured.

Portable Python CI jobs use:

```yaml
runs-on: ${{ vars.SOVEREIGN_CI_RUNNER || 'ubuntu-latest' }}
```

The supported sovereign value is:

```text
self-hosted Linux arm64
```

The default hosted value is:

```text
ubuntu-latest
```

macOS workflows may use `macos-latest` when native Apple/Xcode tooling is actually required.

## Why this changed

The previous policy prohibited GitHub-hosted runners while `python-ci.yml` requested `ubuntu-latest`. That was internally contradictory: the workflow could queue successfully but violated the repository's declared runner policy.

The hybrid model removes that contradiction without hard-coding a single machine. A repository can run normally on GitHub-hosted infrastructure, while an operator with a sovereign ARM64 runner can select it through `SOVEREIGN_CI_RUNNER` without changing workflow source.

## Operational rule

Do not implement automatic runner fallback inside a job. GitHub Actions selects one runner before the job starts; a failed or unavailable self-hosted runner cannot safely be treated as an in-job fallback. The portable default therefore remains hosted Linux unless the operator explicitly selects the sovereign runner.

## Enforcement

Before opening or merging workflow changes:

```bash
python3 scripts/check-runner-policy.py
```

The policy checker must accept the portable hybrid expression and reject unknown runner declarations.

## Scope

- All first-party files under `.github/workflows/*.yml` / `*.yaml`.
- Vendored `external/` content is out of scope for first-party runner enforcement.

## Global portability boundary

CI portability means the project is not tied to one physical host, network, or runner. It does **not** mean every arbitrary device can execute GitHub Actions directly. Device-local execution belongs to the repository's local/offline CI path; GitHub-hosted and sovereign self-hosted runners provide the remote CI execution paths.
