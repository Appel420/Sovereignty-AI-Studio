# CI Runner Policy (Owner Authority)

**Status:** LOCKED  
**Branch authority:** ara-hardened (and all first-party workflows)  
**Judge / executioner:** Human owner

## Required value

```yaml
runs-on: ['self-hosted Linux arm64']
```

## Prohibited

```yaml
ubuntu-latest
macos-latest
macos-15
self-hosted linux
linux Arm64 : ubuntu latest
self-hosted Linux          # incomplete — must include arm64 in the exact form above
```

No GitHub-hosted runners. No mixed fallback. No reinterpretation.

## Enforcement

Before opening a PR or merging workflow changes:

```bash
python3 scripts/check-runner-policy.py
```

Exit code 1 = invalid runner present.

## Scope

- All files under `.github/workflows/*.yml` / `*.yaml`
- `external/` is vendored and out of scope for this policy file’s rewrite rule, but first-party workflows must never point jobs at hosted runners

## WHO / WHAT / WHEN / WHERE / WHY / HOW

| | |
|--|--|
| **WHO** | Owner (Appel420) sets policy; agents must not override |
| **WHAT** | Runner label on every first-party CI job |
| **WHEN** | Every workflow edit, every PR |
| **WHERE** | `.github/workflows/` |
| **WHY** | Denied services must not be reintroduced; self-hosted ARM64 is the canonical runtime |
| **HOW** | Exact `runs-on: ['self-hosted Linux arm64']` + `scripts/check-runner-policy.py` |
