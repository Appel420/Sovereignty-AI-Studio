# Local Integration

This branch adds a device-local integration layer for the Sovereignty repositories.

## Added capabilities

- `integration/local-repositories.json` declares the five sibling repositories and their roles.
- `scripts/setup-local-integration.sh` prepares local sibling checkouts without overwriting existing directories.
- `scripts/local_integration.py check` performs an offline, fail-closed preflight.
- `scripts/start-local-integration.sh` runs the preflight before starting the existing local Studio launcher.
- `docs/LOCAL_INTEGRATION.md` documents repository roles, startup order, and storage boundaries.

## Local use

```bash
chmod +x scripts/setup-local-integration.sh scripts/start-local-integration.sh
./scripts/setup-local-integration.sh
./scripts/start-local-integration.sh
```

The scripts do not create credentials, start cloud agents, enable remote providers, or claim that the system is installed on a device. They operate only after being run locally by the device owner.
