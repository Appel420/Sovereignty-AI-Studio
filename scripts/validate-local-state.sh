#!/usr/bin/env bash
# Validate the local-state contract using local tools only.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m json.tool schemas/local-state/provider-registry.schema.json >/dev/null
python3 -m json.tool schemas/local-state/voice-confirmation.schema.json >/dev/null
python3 -m json.tool registry/provider-registry.example.json >/dev/null

python3 - <<'PY'
import json
from pathlib import Path

registry = json.loads(Path('registry/provider-registry.example.json').read_text())
assert registry['storage_root'] == 'device-local'
assert registry['network'] == 'disabled'
assert registry['external_memory'] == 'disabled'
assert all(provider['network'] is False for provider in registry['providers'])
wake = registry['wake_word']
assert wake['recognition'] == 'local_engine_required'
assert wake['remote_recognition'] is False
assert wake['status'] == 'not_configured'
PY

for file in scripts/create-device-family-tree.sh frontend/public/voice-confirmation.js; do
  if [[ ! -f "$file" ]]; then
    echo "local-state validation failed: expected contract file missing: $file" >&2
    exit 1
  fi
done

if grep -nE '(^|[[:space:]])(curl|wget|git[[:space:]]+clone)([[:space:]]|$)|generate_key|generate_keypair|token_urlsafe|token_hex|os\.urandom' scripts/create-device-family-tree.sh >/dev/null; then
  echo 'local-state validation failed: forbidden network or key-generation pattern found' >&2
  exit 1
fi

if grep -nE '(^|[[:space:]])(curl|wget|git[[:space:]]+clone)([[:space:]]|$)|generate_key|generate_keypair|token_urlsafe|token_hex|os\.urandom' frontend/public/voice-confirmation.js >/dev/null; then
  echo 'local-state validation failed: voice detector has forbidden side effects' >&2
  exit 1
fi

echo 'local-state contract passed'
