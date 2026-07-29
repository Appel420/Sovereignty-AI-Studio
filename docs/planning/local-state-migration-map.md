# Local-State Migration Map

**Status:** prepared in the Studio repository  
**Branch:** `feature/canonical-governance-core`  
**Purpose:** organize the device-local memory/family-tree contract without creating a second repository or moving private device data.

## Decision

Keep the canonical local-state contract in this repository for now. Do not create, clone, or depend on a second repository until the contract has passed local CI and the Human Owner explicitly approves a repository split.

The split is logical, not a second runtime:

```text
Sovereignty-AI-Studio
├── schemas/local-state/       canonical data contracts
├── registry/                  public-safe example metadata
├── policies/                  local-first rules
├── scripts/                   local validators and initializers
├── tests/                     contract tests
└── frontend/                  read-only presentation adapter

Device-local state (never committed)
└── $HOME/Admin/On Device Memory Storage/
    ├── provider-registry.json
    ├── Router/Council/
    ├── audit/
    └── hybrid/
```

## File disposition

### Canonical local-state contract — keep here and organize

| Current file | Destination | Disposition |
|---|---|---|
| `scripts/create-device-family-tree.sh` | same path | Keep as the device-local initializer; later make it schema-driven. |
| `frontend/public/voice-confirmation.js` | same path | Keep as the browser-local confirmation adapter. |
| `frontend/scripts/test-voice-confirmation.js` | same path | Keep as the local JavaScript contract test. |
| `docs/interfaces/device-family-tree.md` | same path | Keep as the normative interface explanation. |
| `docs/audit/SCAR_LOCAL_FIRST_LOG.md` | same path | Keep as repository evidence; never put private runtime logs here. |
| `tests/test_local_integration.py` | same path | Keep as Studio integration coverage. |

### New contract files added by this migration preparation

| File | Purpose |
|---|---|
| `schemas/local-state/provider-registry.schema.json` | Validates public-safe registry structure. |
| `schemas/local-state/voice-confirmation.schema.json` | Defines transcript confirmation results and policy levels. |
| `registry/provider-registry.example.json` | Non-secret example only; not live device state. |
| `policies/local-state-boundary.md` | States ownership, privacy, no-listening, no-key-generation, and no-network rules. |
| `scripts/validate-local-state.sh` | Local validator for schemas, examples, and source boundaries. |
| `tests/test_local_state_contract.py` | Python contract tests that run under local CI. |

### Studio runtime and integration — stays in Studio

```text
frontend/public/index.html
frontend/public/device-family-tree.js
frontend/public/device-family-tree.css
frontend/scripts/verify-sovereign-frontend.js
scripts/local-ci.sh
scripts/local_integration.py
scripts/start-local-integration.sh
scripts/setup-local-integration.sh
config/network-policy.json
scripts/validate-network-policy.py
integration/local-repositories.json
```

These files display or consume local state. They must remain read-only with respect to the canonical registry and must not create replacement state silently.

### Never migrate or commit

```text
$HOME/Admin/On Device Memory Storage/
real provider-registry.json
raw memory and conversations
audio recordings
private SCAR logs
OAuth/API tokens
private keys (*.pem, *.priv, master.key)
.sg_master_key
.sg_token_key
```

### Keep outside the local-state contract

```text
.github/workflows/
Dockerfile
docker-compose*.yml
start-all.sh
START_SERVER.sh
backend/
node-bridge/
gateway/
security_backend.py
token_handler/
external/
```

These are runtime, deployment, credential, legacy, or vendored components. They require separate review and must not define local-state authority.

## Local CI acceptance

The migration is complete only when the following run locally without cloud services, registry access, key generation, or background listening:

```bash
bash -n scripts/create-device-family-tree.sh scripts/validate-local-state.sh
scripts/validate-local-state.sh
node frontend/scripts/test-voice-confirmation.js
python3 -m pytest -q tests/test_local_state_contract.py tests/test_local_integration.py
```

No second repository is required for this stage. A future repository split must preserve these paths and contracts through a reviewed, explicit migration.
