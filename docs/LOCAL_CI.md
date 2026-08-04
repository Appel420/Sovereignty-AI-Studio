# Device-local CI

`run-local-ci.py` is the canonical coordination test runner. It is **not** a
GitHub Actions workflow and it does not install dependencies, dispatch a
runner, call a provider, or publish artifacts.

## Run

```bash
python3 scripts/run-local-ci.py --ci-name coordination-unit-ci-local
# equivalent convenience wrapper
bash scripts/local-ci.sh --ci-name coordination-unit-ci-local
```

By default on Linux the runner re-executes itself in an unshared network
namespace. If the host cannot create that namespace, it exits before tests
start. This protects against accidental provider or package-network calls while
allowing ordinary local file and Git metadata operations.

The runner executes only:

```text
backend/coordination/test_*.py
```

It writes a local verification stamp to `reports/`; the stamp contains metadata
and test exits only, never prompts, credentials, or test payloads.

## Enforcement modes

| Option | Meaning |
| --- | --- |
| `required` (default) | Refuse to run unless Linux network-namespace isolation is active. |
| `best-effort` | Run with offline environment variables if namespace isolation is unavailable; the report labels network enforcement as not enforced. |
| `none` | Explicitly disable namespace isolation; intended only for debugging. |

```bash
python3 scripts/run-local-ci.py \
  --ci-name coordination-unit-ci-local \
  --offline-enforcement best-effort
```

`hybrid` and `online` CI names are deliberately rejected by this runner. They
must use separately reviewed tooling and cannot silently fall back to this
local path.
