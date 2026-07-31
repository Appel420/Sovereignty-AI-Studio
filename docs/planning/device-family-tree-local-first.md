# Device-local family-tree implementation plan

This plan is intentionally constrained to local files, local tests, and local logs.

## Commit 1 — registry script

- Add `scripts/create-device-family-tree.sh`.
- Create the device-local directory tree.
- Write `provider-registry.json` and the audit README.
- Validate with `bash -n`, a temporary `SOVEREIGN_STATE_ROOT`, and `python3 -m json.tool`.
- Do not contact GitHub, providers, cloud runners, or external memory.

## Commit 2 — dashboard

- Render the family tree from embedded local metadata.
- Read `provider-registry.json` only through same-origin local serving.
- Fall back safely when the registry is unavailable.
- Display authorization as `NOT EVALUATED` and SCAR as local-only/unavailable.
- Do not initialize audio, wake-word recognition, provider clients, or background listeners.

## Commit 3 — tests and documentation

- Test the initializer in a temporary directory.
- Test valid JSON, disabled network, disabled external memory, and disabled remote recognition.
- Test that source contains no `curl`, `wget`, clone, provider API, or remote URL path.
- Verify the dashboard has no React/runtime dependency and enforces local registry boundaries.
- Record failures and decisions in local SCAR documentation only.

## Completion rule

A step is complete only when its local validation passes. Missing local engines or ledgers produce explicit unavailable states; they never trigger cloud substitution.
