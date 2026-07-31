# Incremental local CI

`scripts/local-ci.sh` now uses the Git change set instead of rebuilding and
retesting the entire repository on every run.

## Incremental behavior

- Python source changes: compile and lint only changed Python files.
- Node source changes: syntax-check only changed Node files.
- Shell changes: run `bash -n` only on changed shell files.
- Changed Python tests: run only those test modules.
- Frontend changes: run the local frontend verifier.
- Documentation-only changes: skip executable checks.

## Full behavior

The complete suite is reserved for changes to dependencies, lockfiles, build
configuration, workflows, runtime maps, CI scripts, or an explicit request:

```bash
FULL_CI=1 bash scripts/local-ci.sh
```

On GitHub Actions, set `BASE_SHA`/`GITHUB_BASE_SHA` and `HEAD_SHA`/`GITHUB_SHA`
when a merge-base comparison is available. Locally the script uses staged and
unstaged Git changes, then falls back to `HEAD~1..HEAD`.

The `external/` tree is excluded from change detection and remains vendor/
reference content.
