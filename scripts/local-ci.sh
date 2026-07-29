#!/usr/bin/env bash
# Deterministic local CI. No cloud agent, hosted runner, publishing, or provider calls.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m compileall -q --exclude external --exclude .venv .
node --check server_9899.js
node --check node-bridge/server.js
node --check backend/api/providers/index.js
node --check backend/api/providers/local.js
node --check frontend/runtime/transport.js
node --check frontend/runtime/hawking-channel.js
node --check frontend/runtime/sg-hawking-integration.js

bash -n scripts/create-device-family-tree.sh scripts/validate-local-state.sh
scripts/validate-local-state.sh
node frontend/scripts/test-voice-confirmation.js
node frontend/scripts/test-no-ollama.js
node frontend/scripts/test-runtime-transport.js
node frontend/scripts/test-hawking-channel.js
node frontend/scripts/test-sg-hawking-integration.js
node frontend/scripts/verify-sovereign-frontend.js

if [[ -x .venv/bin/pytest ]]; then
  .venv/bin/pytest -q
elif command -v pytest >/dev/null 2>&1; then
  pytest -q
else
  echo "pytest is required for local CI" >&2
  exit 1
fi

echo "local CI passed"
