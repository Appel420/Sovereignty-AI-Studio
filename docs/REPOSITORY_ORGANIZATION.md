# Repository Organization Guide

This document describes the organization structure of the Sovereignty AI Studio repository.

## Directory Structure

### Core Application Directories

- **`backend/`** - FastAPI backend services
  - Main API endpoints
  - Database models and migrations
  - Business logic

- **`frontend/`** - React frontend application
  - User interface components
  - Client-side routing
  - State management

- **`node-bridge/`** - Node.js bridge server
  - HTTP/API bridge on port 9899
  - AI agent integration proxy
  - Service orchestration

### Source Code

- **`src/crypto/`** - Cryptography implementations
  - C/C++ header files (.hpp)
  - Falcon post-quantum signature algorithm
  - NTRU lattice-based cryptography
  - Benchmark and test files

- **`src/system-calls/`** - System call implementations
  - Low-level C implementations (.c)
  - Header files (.h)
  - System utilities

### Documentation

- **`docs/html/`** - HTML documentation and dashboards
  - HIPAA audit reports
  - Global role dashboards
  - Medical education materials
  - Compliance visualizations

- **`docs/planning/`** - Planning and process documentation
  - Architecture planning
  - Implementation guides
  - Development workflows
  - Multi-agent orchestration plans

- **`docs/compliance/`** - Compliance and regulatory documentation
  - HIPAA compliance documents
  - ISO/IEC standards
  - Automation policies
  - Forbidden words policies

### Scripts and Automation

- **`scripts/python/`** - Python utility scripts
  - Forbidden words filter
  - Battleships game
  - EEG streaming utilities
  - Silicon Flow integration
  - Immutable logger

- **`scripts/shell/`** - Shell scripts for automation
  - Setup scripts
  - Start scripts
  - Build automation

### AI Agents

- **`ai_agents/`** - AI agent implementations
  - Judge build agent
  - Repository maintenance agent
  - Custom AI automation scripts

### Other Directories

- **`external/`** - Vendored third-party source
  - `SuperGrok-Heavy-4-2-Skeleton/` is a managed external workspace
  - `python-keycloak/` is the vendored Keycloak client distribution
  - External projects are not imported by the root runtime or covered by root checks

- **`archives/`** - Archived historical artifacts, if retained
  - ZIP archives and immutable snapshots only
  - No archive is a runtime dependency

- **`resources/`** - Static resources and assets
- **`tests/`** - Test files
- **`test/`** - Additional test utilities
- **`crypto/`** - Crypto-related utilities (legacy)
- **`ai_core/`** - AI core functionality
- **`sovereignty_ai/`** - Sovereignty AI specific modules

## Root Files

The following files should remain in the root directory:

### Configuration Files
- `.env.example` - Environment variable template
- `.flake8` - Python linting configuration
- `.gitignore` - Git ignore rules
- `docker-compose.yml` - Docker services configuration
- `Dockerfile` - Docker image definition
- `Makefile` - Build automation
- `package.json` - Node.js dependencies
- `package-lock.json` - Locked dependencies
- `pytest.ini` - Python test configuration
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - Main project documentation
- `LICENSE` / `LICENSE.MD` - License information
- `SECURITY.md` - Security policy
- `PORT_ALLOCATION.md` - Port allocation guide

### Server Files
- `bridge.py` - Python bridge server on port 9897
- `unified_server.js` - Unified JavaScript server on port 9899
- `server_9899.js` - Node bridge server on port 9899
- `security_backend.py` - Security backend service
- `security_layer.js` - Security layer implementation
- `weather_dashboard.py` - Weather dashboard service
- `node-bridge.mjs` - Node bridge module

### Startup Scripts
- `start-all.sh` - Start all services script
- `START_SERVER.sh` - Server startup script

## Maintenance

### Automated Maintenance

Run the maintenance agent to check repository organization:

```bash
python3 ai_agents/repo_maintenance_agent.py
```

This may:
- Verify directory structure
- Detect misplaced files
- Find duplicate files
- Identify empty files
- Suggest corrective actions

### Manual Cleanup

When adding new files:

1. **C/C++ crypto code** → `src/crypto/`
2. **System calls** → `src/system-calls/`
3. **HTML docs** → `docs/html/`
4. **Planning docs** → `docs/planning/`
5. **Python utilities** → `scripts/python/`
6. **Shell scripts** → `scripts/shell/`
7. **AI agents** → `ai_agents/`
8. **Archives** → `archives/`

### Linting

The `.flake8` configuration excludes:
- Third-party code
- Generated files
- Archived content
- Crypto implementations
- System-level code

Run linting:
```bash
flake8 .
```

## Best Practices

1. **Keep root directory clean** - Only essential config and server files
2. **Use descriptive names** - Avoid generic names like "test.py"
3. **Remove duplicates** - Files with " 2" suffix should be reviewed
4. **Document changes** - Update the repository inventory when ownership changes
5. **Run maintenance agent** - Periodically check organization
6. **Do not add runtime code to `external/` or `archives/`** - Promote reviewed code into a canonical directory first

## CI/CD Integration

The repository uses GitHub Actions for CI/CD. The cleanup maintains compatibility with:
- Python linting (flake8)
- Python testing (pytest)
- Node.js testing
- Docker builds

Root CI and development checks deliberately exclude `external/`; each vendor
project retains its own upstream checks and metadata.
