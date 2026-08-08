# Local CI

`run-local-ci.py` is the canonical local coordination test runner. It is **not** a GitHub Actions workflow and it does not install dependencies, dispatch a runner, call a provider, or publish artifacts.

## Run

```bash
python3 scripts/run-local-ci.py --ci-name ara-hardened-unit-ci-local
# equivalent convenience wrapper
bash scripts/local-ci.sh --ci-name ara-hardened-unit-ci-local
```

By default the runner executes locally and writes a verification stamp to `reports/`.

The runner executes the local coordination and accessibility checks that are present in the repository.

```text
backend/coordination/
prototypes/accessibility/tests/test_accessibility_control.py
```

It writes a local verification stamp to `reports/`; the stamp contains metadata and test exits only, never prompts, credentials, or test payloads.

## Modes

| Option | Meaning |
| --- | --- |
| `local` (default) | Run the local CI checks on this machine. |
| `hybrid` | Requires explicit confirmation with `--confirm-mode hybrid`. |
| `online` | Requires explicit confirmation with `--confirm-mode online`. |

```bash
python3 scripts/run-local-ci.py \
  --ci-name ara-hardened-unit-ci-local \
  --why "offline validation"
```

`hybrid` and `online` CI names are deliberately rejected by this runner unless confirmed. They must use separately reviewed tooling and cannot silently fall back to this local path.
