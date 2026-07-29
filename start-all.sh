#!/usr/bin/env bash
# Compatibility entrypoint. START_SERVER.sh is the only supported launcher.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT_DIR/START_SERVER.sh" "$@"
