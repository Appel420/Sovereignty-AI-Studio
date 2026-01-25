Sovereignty AI Project Directory Structure (Grouped by Category)
Last Updated: January 25, 2026

1. Applications
apps/
├── backend/              # FastAPI service
│   ├── Dockerfile
│   ├── alembic/
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── main.py
│   │   ├── config.py
│   │   └── dependencies.py
│   └── requirements.txt
├── frontend/             # React/TypeScript UI
│   ├── Dockerfile
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── tsconfig.json
└── familyguard/          # Dedicated Swift client UI
    ├── FamilyGuard.html
    └── VoiceCommandIntegrity.swift

2. Core AI
ai_core/                  # Sovereign high-sensitivity zone
├── AI-Lie-Detector.py
├── Scar-Keep.py
├── Scar-Memory.py
├── Scar-keep-tamper.py
├── QuantumModel.py
├── Sovereignty_core.py
├── sovereign_mind.py
├── Reasoning.py
├── Verifier.py
├── Voice_Guard.py
├── Syntax-Guard.py
├── SuperGrok-Heavy-4-2.py
└── quantum_layer.py

3. Agents
agents/                   # Specialized autonomous agents
├── Coach_agent.py
├── Pieces_Agent.py
├── Second_Squad_Agent.py
├── eeg_agent.py
├── eyes_agent.py
└── …

4. Domains
domains/                  # Grouped specialized logic
├── vision/               # Former vision/
├── logic/                # Former logic/ (resolvent.py, bfs_nav.py, etc.)
├── medical/              # Former medical/ (diag_router.py, waveform_7.py, etc.)
└── vault/                # Former vault/ (qresist.py, blake3.py, argon2.py, Vault_crypto.js)

5. Infrastructure
orchestrator/             # Workflow and system control
├── go_main.go
└── breath.py

firmware/                 # Embedded systems
└── src/
    └── ESP42.bin         # Temporary blob

platform/                 # Language-specific low-level code
├── rust/
│   ├── Alerts.Rust
│   ├── Fortress-Protocol-7.887.Rust
│   ├── Cargo.toml
│   └── build.rs
└── swift/
    ├── Main.swift
    └── Honey.swift

scripts/                  # Operational utilities
├── deploy.sh
├── backup_db.sh
└── …

root_scripts/             # Legacy quarantine (deprecated)

6. Testing
tests/                    # Top-level priority
├── backend/
├── frontend/
├── ai_core/
└── e2e/

7. Documentation
docs/
└── ar/

misc/                     # Miscellaneous resources
.github/workflows/
├── static.yml
└── …                     # e.g., test-backend.yml, lint.yml

LICENSE                   # Mozilla Public License 2.0
README.md                 # Expanded
SECURITY.md
Structure                 # This file

.env.example               # Environment reference
Docker-compose.yml         # Added for container orchestration

Summary:
Directories are grouped into Applications, Core AI, Agents, Domains, Infrastructure, Testing, and Documentation for clarity.
platform/ and scripts/ are part of Infrastructure.
tests/ is a first-class top-level directory.
root_scripts/ remains for deprecated tools only.
