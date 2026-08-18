# SGHV119 Local Maintenance Runner

`scripts/sghv119-maintenance.py` is a read-only verification runner for the SGHV119 runtime boundary.

## Contract

- Offline/read-only by design.
- Does not authorize operations.
- Does not execute repository mutations.
- Does not contact AI providers or external services.
- Reports branch and commit provenance.
- Fails closed when required runtime surfaces or boundary markers are missing.
- A `PASS` means the inspected maintenance checks passed; it does **not** grant authority or make a change admissible for merge.

## Usage

```bash
python3 scripts/sghv119-maintenance.py
python3 scripts/sghv119-maintenance.py --json
```

For DevAssist, this runner should be invoked only after an existing `ALLOW` decision and within the authorized local execution scope. The runner itself cannot create that authorization.

## Checks

1. Protected-branch boundary.
2. SGHV119/runtime contract presence.
3. Python syntax for the local coordination surface.
4. JSON configuration validity.
5. SGHV119 state vocabulary and offline transport contract markers.
6. DevAssist execution-boundary markers.

The runner intentionally produces verification state rather than changing project state. Evidence/admission remains the responsibility of the surrounding control plane.
