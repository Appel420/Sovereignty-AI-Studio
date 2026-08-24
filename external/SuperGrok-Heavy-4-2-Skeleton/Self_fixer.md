### Role
Act as an experienced **distributed systems architect and polyglot principal engineer (Python + Node.js)** specializing in secure event pipelines, verification systems, and autonomous AI infrastructure.

### Task
Implement a **fully working single-port bridge (port 9897)** that connects the **Self-Fixer AI Python system** with the **SuperGrok-Heavy-4-2-Skeleton Merkle verification module**.

The bridge must:

- run **one gateway service on port 9897**
- spawn a **Node Merkle worker internally**
- route **all events, verification requests, and metrics through the gateway**
- integrate with the **SelfFixer runtime**
- expose monitoring endpoints for dashboards

The final implementation should be **clean, runnable, and under ~350–400 lines of new code**.

---

### Context

#### Repo A — Self-Fixer AI (Python)

Structure:

selffixerai/
├── core/
│   ├── self_fixer.py
│   └── backup_manager.py
├── security/
│   ├── encryption.py
│   └── tamper_lock.py
├── analysis/
│   └── deep_scanner.py
├── monitoring/
├── dashboard/
└── main.py

Capabilities:
- self-healing runtime
- encrypted backups
- Ed25519 tamper detection
- ChaCha20 encrypted state
- static analysis scanning
- monitoring + dashboards

---

#### Repo B — SuperGrok-Heavy-4-2-Skeleton

Key component:

merkle.js

Implements **RFC6962 Merkle inclusion verification**.

---

### Bridge Architecture

Create directory:
