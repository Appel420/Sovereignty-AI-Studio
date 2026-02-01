Sovereignty AI Project Directory Structure (Grouped by Category)
Last Updated: February 1, 2026

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
├── quantum_layer.py
├── Reasoning.py
├── Scar-Keep.py
├── Scar-keep-tamper.py
├── Scar-Memory.py
├── second_squad_agent.py
├── sovereign_mind.py
├── Sovereignty_core.py
├── Syntax-Guard.py
├── Verifier.py
└── Voice_Guard.py

3. Agents
agents/                   # Specialized autonomous agents
├── Coach_agent.py
├── eeg_agent.py
├── eyes_agent.py
├── Pieces_Agent.py
└── Second_Squad_Agent.py

4. Domains
domains/                  # Grouped specialized logic
├── vision/
├── logic/
│   ├── bfs_nav.py
│   └── resolvent.py
├── medical/
│   ├── diag_router.py
│   └── waveform_7.py
└── vault/
    ├── argon2.py
    ├── blake3.py
    ├── qresist.py
    └── Vault_crypto.js

5. Infrastructure
orchestrator/             # Workflow and system control
├── breath.py
└── go_main.go

platform/                 # Language-specific low-level code
├── rust/
│   ├── Alerts.Rust
���   ├── build.rs
│   ├── Cargo.toml
│   └── Fortress-Protocol-7.887.Rust
└── swift/
    ├── Honey.swift
    └── Main.swift

scripts/                  # Operational utilities
├── backup_db.sh
└── deploy.sh

6. Testing
tests/                    # Top-level priority
├── ai_core/
├── backend/
├── e2e/
└── frontend/

7. Documentation
docs/
└── ar/

.github/
└── workflows/
    ├── lint.yml
    ├── static.yml
    └── test-backend.yml

LICENSE                   # Mozilla Public License 2.0
README.md                 # Expanded
SECURITY.md
Structure                 # Plain text structure file
Structure.md              # This markdown structure file

.env.example              # Environment reference
docker-compose.yml        # Container orchestration

Summary:
Directories are grouped into Applications, Core AI, Agents, Domains, Infrastructure, Testing, and Documentation for clarity.
platform/ and scripts/ are part of Infrastructure.
tests/ is a first-class top-level directory.
All files and directories are organized professionally, with outdated or temporary items removed.