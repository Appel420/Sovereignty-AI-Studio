# Python linting

Pylint was previously configured with `|| true`, which made failures invisible and allowed CI to pass while the lint job was failing. That has been removed.

## Run the configured scope

```bash
make py-lint
```

The command is blocking: a non-zero Pylint exit code fails the target. The scope remains explicit in `Makefile`, and vendored or intentionally deferred legacy modules remain excluded through `PYLINT_IGNORE_PATHS`.

## Run all local checks

```bash
bash scripts/local-ci.sh
```

This runs the runtime-coherence checks, JavaScript checks, Pylint, and tests. No lint command should use `|| true` to hide a failure.

## Fix order

When Pylint reports issues, fix them in this order:

1. Syntax/import failures and undefined names.
2. Exceptions that hide failures or use overly broad handling.
3. Security findings involving subprocesses, dynamic execution, credentials, or unsafe deserialization.
4. Type and interface mismatches at service boundaries.
5. Naming, docstrings, line length, and other style warnings.

Do not suppress a warning globally just to get a green run. Use a narrow inline disable only when the behavior is deliberate, documented, and reviewed.
