Sovereignty AI Project Directory Structure (Grouped by Category)
Last Updated: January 28, 2026

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
├── Sovereignty_core.py
├── sovereign_mind.py
├── Reasoning.py
├── Verifier.py
├── Voice_Guard.py
├── Syntax-Guard.py
├── quantum_layer.py
└── second_squad_agent.py

3. Agents
agents/                   # Specialized autonomous agents
├── Coach_agent.py
├── Pieces_Agent.py
├── Second_Squad_Agent.py
├── eeg_agent.py
└── eyes_agent.py

4. Domains
domains/                  # Grouped specialized logic
├── vision/
├── logic/
│   ├── resolvent.py
│   └── bfs_nav.py
├── medical/
│   ├── diag_router.py
│   └── waveform_7.py
└── vault/
    ├── qresist.py
    ├── blake3.py
    ├── argon2.py
    └── Vault_crypto.js

5. Infrastructure
orchestrator/             # Workflow and system control
├── go_main.go
└── breath.py

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
└── backup_db.sh

6. Testing
tests/                    # Top-level priority
├── backend/
├── frontend/
├── ai_core/
└── e2e/

7. Documentation
docs/
└── ar/

.github/
└── workflows/
    ├── static.yml
    ├── test-backend.yml
    └── lint.yml

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