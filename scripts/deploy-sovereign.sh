#!/usr/bin/env bash
set -Eeuo pipefail

commit="${1:?commit SHA required}"
root="${SOVEREIGN_RELEASE_ROOT:-/var/lib/sovereignty/releases}"
current="${SOVEREIGN_CURRENT_LINK:-/var/lib/sovereignty/current}"
source_dist="${SOVEREIGN_SOURCE_DIST:-dist}"
scar_root="${SOVEREIGN_SCAR_ROOT:-/var/lib/sovereignty/scar}"
release="${root}/${commit}"

mkdir -p "${root}" "${scar_root}"
test -d "${source_dist}"
test -n "$(find "${source_dist}" -maxdepth 1 -type f -print -quit)"

rm -rf "${release}.staging"
mkdir -p "${release}.staging"
cp -a "${source_dist}/." "${release}.staging/"
sha256sum "${release}.staging"/* > "${release}.staging/SHA256SUMS"
mv "${release}.staging" "${release}"

ln -sfn "${release}" "${current}.next"
mv -Tf "${current}.next" "${current}"

python - <<'PY' "${commit}" "${release}" "${scar_root}/deployment-receipt.json"
import json
import os
import sys
import time
from pathlib import Path

commit, release, output = sys.argv[1:]
payload = {
    "schema": "SCAR-DEPLOYMENT-RECEIPT-v1",
    "timestamp": int(time.time()),
    "commit": commit,
    "release_path": release,
    "current_link": os.environ.get("SOVEREIGN_CURRENT_LINK", "/var/lib/sovereignty/current"),
    "status": "DEPLOYED",
}
path = Path(output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
PY

printf 'SOVEREIGN_ARTIFACT_DEPLOYMENT=PASS\n'
printf 'SOVEREIGN_RELEASE=%s\n' "${release}"
printf 'SOVEREIGN_CURRENT=%s\n' "${current}"
