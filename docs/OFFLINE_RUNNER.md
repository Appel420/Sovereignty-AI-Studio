# Offline runner

`scripts/offline-runner.sh` is the repository-local execution path for the
Sovereignty-AI-Studio build surface. It does not use GitHub Actions, a hosted
runner, package registries, artifact uploads, or git push.

## Run

```bash
bash scripts/offline-runner.sh
```

The runner:

1. acquires a local lock so two runs cannot collide;
2. forces offline/local environment settings;
3. checks shell syntax;
4. runs the Hawking channel/runtime tests when present;
5. runs runtime and local-state validation when present;
6. invokes the canonical `scripts/local-ci.sh` runner;
7. writes a JSON report and log under `reports/`.

To start the local service graph after validation instead of returning to the
shell, use the explicit owner-controlled option:

```bash
OFFLINE_CI_START_SERVICES=1 bash scripts/offline-runner.sh
```

This calls the existing `START_SERVER.sh`; it does not install dependencies or
contact external services. The required local services and dependencies must
already exist on the device.

If the runner says another run is active, inspect the process first. Only remove
`.offline-ci.lock` after confirming no offline runner is running.
