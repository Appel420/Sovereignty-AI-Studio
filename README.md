# Sovereignty AI Studio ⚔️

[![CI](https://github.com/Appel420/Sovereignty-AI-Studio/workflows/CI/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions)
[![codecov](https://codecov.io/gh/Appel420/Sovereignty-AI-Studio/branch/main/graph/badge.svg)](https://codecov.io/gh/Appel420/Sovereignty-AI-Studio)

> **Zero third-party vendor lock-in.  No Google. No Meta. No Llama.cpp No Vercel.**
> All AI inference is local and stays on your infrastructure.

**Private Sovereign AI Research and Development Platform**
**Core Model:** Super Grok Heavy 4.2 (xAI) – Locked, Sealed, Sovereign
**Authority:** Derek Appel
**Last Updated:** May 4, 2026

---

## Overview

Sovereignty AI Studio is a fully private, self-contained research and production environment for advanced sovereign artificial intelligence systems.

The platform integrates specialized domains including computer vision, logical reasoning, biomedical signal processing, cryptographic vaulting, autonomous agents, and system orchestration. All components are designed for complete operational independence, end-to-end encryption, and tamper-resistant execution.

No external services, third-party models, or internet connectivity are required for core operation.

*From Hello to Goodbye — Sovereignty AI Studio is a sovereign platform for the people.*

---

## Architecture

```
Browser / iPhone
   │
   ├─── HTTP GET http://localhost:9898/SGHv119.html  ──► KODER frontend (static server)
   │
   └─── WebSocket/API http://localhost:9899/...  ──► node-bridge (gateway)
                                                          │ proxy
                                                          ▼
                                                   Python bridge.py (9897)
                                                          │
                                                          ▼
                                                   backend (FastAPI :8002, internal)
                                                       ┌──┴──────────────┐
                                                       ▼                 ▼
                                               PostgreSQL (5432)   Redis (6379)
```

The UI is served at **port 9898** (static file server, non-Docker). All WebSocket and HTTP API traffic from the browser goes to **port 9899** (node-bridge), which proxies AI/TTS/memory/STT messages to the Python bridge at **port 9897**. Backend, database, and Redis remain on the internal Docker network.

| Service | Port | Notes |
|---------|------|-------|
| KODER frontend (SGHv119.html) | 9898 | Static file server (non-Docker) |
| node-bridge (gateway) | 9899 | WebSocket + HTTP API proxy |
| Python bridge (bridge.py) | 9897 | Primary AI/WS backend |
| backend (FastAPI) | internal | Routed via node-bridge |
| PostgreSQL 16 | internal | Initializes from `db/schema.sql` |
| Redis 7 | internal | Cache + session store |

---

## Prerequisites

- Python 3.12.x (CI target; 3.10+ should work)
- Node.js >= 20.0.0 for the bridge and unified servers
- Docker + Docker Compose for containerized workflows

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env — set JWT_SECRET, database passwords, model paths

# 2. Start the stack
docker compose up -d

# 3. Check health
curl http://localhost:9899/health
```

For production with TLS and static assets, enable the bundled Nginx reverse proxy:

```bash
docker compose --profile production up -d
```

---

## Key Components

| Path | Purpose |
| --- | --- |
| `SGHv119.html` | KODER — main sovereign dashboard (SuperGrok Heavy 4.2 Enterprise UI) |
| `ai_core/sovereign_bridge.py` | Python sovereign AI bridge — routes all inference locally |
| `node-bridge/server.js` | Node.js WebSocket + HTTP bridge proxy (port 9899) |
| `bridge.py` | Python WebSocket bridge server (port 9897) |
| `scripts/javascript/sanitizer.js` | Enterprise-grade sanitizer with circuit-breaker syslog, log rotation, correlation IDs |
| `db/schema.sql` | Postgres schema (users, orgs, memberships, projects, usage, audit) |
| `backend/app/api/v1` | FastAPI endpoints (auth, orgs, media, voice, telemetry, etc.) |
| `frontend/src/views` | React views, including organization management |
| `ios/` | iOS Swift Package (SovereigntyGuard) with debugger detection and audit logging |
| `ai_core/` | Core AI modules (lie detector, defense module, Ara core) |
| `apps/dashboards/` | Dashboard applications including post-quantum and EEG dashboards |
| `crypto/` | Cryptography modules |
| `docs/` | Hardware and research documentation |
| `docker-compose.yml` | Self-hosted stack (Postgres, Redis, Backend, Bridge, Nginx) |
| `eeg_streaming.py` | Real-time EEG signal acquisition, band power analysis, and SSE broadcasting |
| `Backend_API_AUTH.py` | Post-quantum authentication router (Dilithium2 + TOTP) |

---

## Sovereignty One Water Systems

The `firmware/esp32_controller.ino` controls a CDI+MED hybrid water purification system:
- Pump control based on PV voltage + TDS thresholds
- Anti-scaling polarity reversal every 15 minutes
- Safety interlocks (over-pressure, over-temperature)
- 1 Hz JSON telemetry via Serial

See [docs/sovereignty_one.md](docs/sovereignty_one.md) for full technical documentation.

---

## Project Structure

```
Sovereignty-AI-Studio/
├── .devcontainer/                 # Dev Container configuration
│   ├── devcontainer.json
│   ├── Ara.yml
│   └── ...
├── .github/                       # GitHub Actions CI workflows
│   └── workflows/
├── src/                           # Source code
│   ├── agents/                    # AI Agent Modules
│   ├── core/                      # Core System Files
│   ├── security/                  # Security & Protection Modules
│   ├── models/                    # Machine Learning Models
│   ├── utils/                     # Utility Functions
│   ├── ai_core/                   # Siri-Replace / Ara Core
│   └── native/                    # Native Code (C++, Swift, Rust)
├── backend/                       # FastAPI backend (surfaced via bridge on port 9899)
│   ├── app/
│   │   ├── api/v1/                # REST & WebSocket API endpoints
│   │   ├── core/                  # Database, security, WebSocket hub
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic schemas
│   │   └── services/              # Business logic (alerts, TTS, users)
│   ├── alembic/                   # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                      # React TypeScript frontend
│   └── src/
│       ├── Frontend_src_Auth.jsx  # Post-quantum auth login component
│       ├── xai_in_cert_Chain.html # xAI certificate chain viewer
│       ├── components/            # Alert center, layout components
│       ├── hooks/                 # WebSocket and alert hooks
│       ├── pages/                 # Dashboard, generator pages
│       └── services/              # API client services
├── apps/
│   ├── dashboards/                # Dashboard Applications
│   │   ├── Tools_Post_Quantum_Dashboard.html
│   │   ├── Real_Validator.html
│   │   └── SuperGrok-Heavy4-2-Validator.html
│   └── web/                       # Web Applications
│       ├── Server.js
│       └── Deploy.html
├── ios/                           # iOS Swift Package (SovereigntyGuard)
│   └── Sources/SovereigntyGuard/
│       ├── ContentView.swift
│       ├── SovereigntyAPIClient.swift
│       ├── AuditLogger.swift
│       ├── DebuggerDetection.swift
│       ├── FamilyGuardCore.swift
│       └── VoiceCommandIntegrity.swift
├── node-bridge/                   # Node.js Bridge (frontend ↔ Python backends)
│   ├── server.js
│   ├── package.json
│   └── test/bridge.test.js
├── ai_core/                       # Core AI modules
│   ├── AI_Core.py
│   ├── Siri_Replace_Ara-Core.py
│   ├── ai_defense_module.py
│   ├── lie_detector.py
│   └── second_squad_agent.py
├── scripts/
│   ├── javascript/
│   │   └── sanitizer.js           # Enterprise sanitizer (circuit-breaker, TLS syslog, gzip rotation)
│   └── python/                    # Python utility scripts
├── crypto/                        # Cryptography Modules
│   └── Vault_crypto.js
├── docs/                          # Documentation
├── SGHv119.html                   # KODER — SuperGrok Heavy 4.2 Enterprise Dashboard (main UI)
├── Backend_API_AUTH.py            # Post-quantum backend auth router (Dilithium2 + TOTP)
├── eeg_streaming.py               # Real-time EEG signal streaming & analysis
├── weather_dashboard.py           # Quart weather dashboard entry point
├── LICENSE.MD
├── SECURITY.md
└── README.md
```

## AI Agent Integration

Sovereignty AI Studio provides seamless integration with multiple AI agents, enabling you to connect with Claude, GPT, Grok, and GitHub Copilot in a unified, secure environment.

### Supported AI Agents

The platform integrates with four major AI providers through a WebSocket-based routing system:

1. **Claude (Anthropic)** - Claude Opus-4.6 via `api.anthropic.com`
2. **GPT (OpenAI)** - GPT-5.4-codex-max via `api.openai.com`
3. **Grok (xAI)** - SuperGrok-4-2-code-fast via `api.x.ai`
4. **GitHub Copilot** - Native integration via GitHub OAuth

### Agent Connection Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Multi-Agent Connection System                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Client Applications                                      │
│  ├─ Frontend (React TS)                                  │
│  ├─ iOS (Swift)                                          │
│  └─ iSH/Code Pad                                         │
│           ↓                                               │
│  ┌────────────────────────────────────┐                 │
│  │  WebSocket Bridge (Port 9899)      │                 │
│  │  server_9899.js / unified_server   │                 │
│  └────────────────────────────────────┘                 │
│           ↓                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │         AI Agent Router (aiProxy)                │    │
│  ├─────────────────────────────────────────────────┤    │
│  │  ANTHROPIC_API_KEY → api.anthropic.com          │    │
│  │  OPENAI_API_KEY    → api.openai.com             │    │
│  │  XAI_API_KEY       → api.x.ai                   │    │
│  │  GH_CLIENT_*       → github.com (OAuth)          │    │
│  └─────────────────────────────────────────────────┘    │
│           ↓                                               │
│  Real-time responses with audit logging                  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```


### Agent Request Protocol

Connect to any agent via WebSocket using the following message format:

```javascript
// Send agent request
{
  type: 'agent_request',
  agent: 'claude' | 'gpt' | 'grok',
  payload: {
    prompt: 'Your question or instruction',
    system: 'Optional system prompt'
  }
}

// Receive agent response
{
  type: 'agent_response',
  agent: 'claude',
  payload: {
    text: 'Agent response text'
  },
  ts: 1234567890
}
```


**Key Features:**
- Maximum prompt length: 128000 characters
- Maximum tokens per response: 8192
- Rate limiting: 30 messages/minute per connection
- Automatic API key validation
- Full audit logging for compliance

### Environment Setup

Create a `.env` file in the project root with your API keys:

```bash
# AI Agent API Keys
ANTHROPIC_API_KEY=sk-ant-...      # Required for Claude
OPENAI_API_KEY=sk-...              # Required for GPT
XAI_API_KEY=xai-...                # Required for Grok

# GitHub OAuth (for Copilot integration)
GH_CLIENT_ID=your_github_client_id
GH_CLIENT_SECRET=your_github_client_secret

# Optional: Server Configuration
PORT_UNIFIED=9001                  # Unified server port
PORT_BRIDGE=9899                   # Bridge server port
LOG_DIR=./logs                     # Audit log directory
VERBOSE=1                          # Enable verbose logging

# Optional: HTTPS/TLS (see scripts/generate-certs.sh)
TLS_CERT=./certs/cert.pem         # Path to TLS certificate
TLS_KEY=./certs/key.pem           # Path to TLS private key
```


**HTTPS Support:**
- Run `./scripts/generate-certs.sh` to generate self-signed certs for local dev
- Set `TLS_CERT` and `TLS_KEY` in `.env` to enable HTTPS on node-bridge and unified server
- In production (Docker), nginx terminates TLS on port 443 and proxies to the internal services
- Without certs, all services default to HTTP (no changes required for local development)

**Security Notes:**
- Never commit API keys to version control
- Use `.gitignore` to exclude `.env` files
- Rotate keys regularly
- Monitor audit logs in `./logs/audit.jsonl`

### Agent Servers

The repository includes two agent bridge servers:

#### 1. Standalone Bridge Server (server_9899.js)

Primary WebSocket bridge for agent routing:

```bash
# Install dependencies (Node 20+)
npm install

# Start the server
node server_9899.js
```


**Endpoints:**
- `ws://localhost:9899` - WebSocket agent routing
- `GET /health` - Health check
- `GET /api/audit` - Audit log viewer
- `POST /api/execute-command` - Command execution (requires auth)

#### 2. Unified Server (unified_server.js)

Comprehensive server with additional features:

```bash
# Install dependencies (Node 20+)
npm install

# Start the server
node unified_server.js
```


**Additional Features:**
- GitHub OAuth authentication
- DuckDuckGo search proxy
- Piper TTS integration
- Role-based access control (30+ roles)
- Multi-factor authentication

### GitHub Copilot Integration

GitHub Copilot is integrated via the GitHub OAuth workflow:

1. **Configure GitHub OAuth App**
   - Go to GitHub Settings → Developer Settings → OAuth Apps
   - Create a new OAuth App with callback URL: `http://localhost:9899/api/gh/callback`
   - Copy Client ID and Client Secret to `.env`

2. **Authenticate**
   ```bash
   # Start unified server
   node unified_server.js

   # Navigate to auth endpoint
   curl http://localhost:9899/api/gh/login
   ```

3. **Use Copilot Features**
   - Code suggestions in your IDE
   - Pull request summaries
   - Code review assistance

### Testing Agent Connections

Test your agent setup with the included test suite:

```bash
# Test agent routing
node --test test/server9899-agent-routing.test.js

# Test server endpoints
node --test test/server9898.test.js

# Run both Node bridge tests together
node --test test/server9899-agent-routing.test.js test/server9898.test.js
```


**Example Test:**

```javascript
// Test Claude agent connection
const ws = new WebSocket('ws://localhost:9899');

ws.on('open', () => {
  ws.send(JSON.stringify({
    type: 'agent_request',
    agent: 'claude',
    payload: {
      prompt: 'Hello, Claude! Can you hear me?',
      system: 'You are a helpful AI assistant.'
    }
  }));
});

ws.on('message', (data) => {
  const response = JSON.parse(data);
  console.log('Agent:', response.agent);
  console.log('Response:', response.payload.text);
});
```

### Agent Usage Best Practices

1. **Keep Prompts Concise**
   - Stay under 8961 characters for optimal performance
   - Use clear, specific instructions

2. **Handle Errors Gracefully**
   - Check for `payload.error` in responses
   - Common errors: Missing API key, rate limit exceeded, network timeout

3. **Monitor Rate Limits**
   - Stay under 30 requests/minute per connection
   - Implement exponential backoff for retries

4. **Use System Prompts Effectively**
   - Define agent behavior and constraints
   - Specify output format requirements

5. **Review Audit Logs**
   - Check `./logs/audit.jsonl` for all agent interactions
   - Monitor for unusual patterns or errors

### Integration Examples

#### Frontend Integration (React/TypeScript)

```typescript
import { useEffect, useState } from 'react';

function AgentChat() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [response, setResponse] = useState('');

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:9899');

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'agent_response') {
        setResponse(data.payload.text || data.payload.error);
      }
    };

    setWs(socket);
    return () => socket.close();
  }, []);

  const askAgent = (agent: string, prompt: string) => {
    ws?.send(JSON.stringify({
      type: 'agent_request',
      agent,
      payload: { prompt }
    }));
  };

  return (
    <div>
      <button onClick={() => askAgent('claude', 'Hello!')}>Ask Claude</button>
      <button onClick={() => askAgent('gpt', 'Hello!')}>Ask GPT</button>
      <button onClick={() => askAgent('grok', 'Hello!')}>Ask Grok</button>
      <pre>{response}</pre>
    </div>
  );
}
```


#### iOS Integration (Swift)

```swift
import Foundation

class AgentClient {
    private var webSocket: URLSessionWebSocketTask?

    func connect() {
        let url = URL(string: "ws://localhost:9899")!
        webSocket = URLSession.shared.webSocketTask(with: url)
        webSocket?.resume()
        receiveMessage()
    }

    func askAgent(_ agent: String, prompt: String) {
        let request: [String: Any] = [
            "type": "agent_request",
            "agent": agent,
            "payload": ["prompt": prompt]
        ]

        let data = try! JSONSerialization.data(withJSONObject: request)
        let message = URLSessionWebSocketTask.Message.data(data)
        webSocket?.send(message) { error in
            if let error = error {
                print("Send error: \(error)")
            }
        }
    }

    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                if case .data(let data) = message {
                    let json = try? JSONSerialization.jsonObject(with: data)
                    print("Response: \(json ?? [:])")
                }
                self?.receiveMessage()
            case .failure(let error):
                print("Receive error: \(error)")
            }
        }
    }
}
```


#### Python Integration

```python
import asyncio
import websockets
import json

async def ask_agent(agent: str, prompt: str):
    uri = "ws://localhost:9899"

    async with websockets.connect(uri) as ws:
        # Send request
        request = {
            "type": "agent_request",
            "agent": agent,
            "payload": {
                "prompt": prompt,
                "system": "You are a helpful assistant."
            }
        }
        await ws.send(json.dumps(request))

        # Receive response
        response = await ws.recv()
        data = json.loads(response)

        if data.get("type") == "agent_response":
            print(f"Agent: {data['agent']}")
            print(f"Response: {data['payload'].get('text', data['payload'].get('error'))}")

# Example usage
asyncio.run(ask_agent("claude", "What is the meaning of life?"))
```


### Maintaining a Clean Environment

The platform is designed to maintain a sanitized, self-updating environment:

1. **Automated Code Cleanup**
   - `.github/agents/my-agent.agent.md` - Template for cleanup agents
   - Removes outdated dependencies
   - Fixes syntax errors automatically
   - Organizes files into appropriate folders

2. **Structure Maintenance**
   - Files are automatically placed in correct locations
   - Folder structure is validated on startup
   - Unused imports and dependencies are flagged

3. **Continuous Integration**
   - GitHub Actions workflow validates code quality
   - Flake8 linting for Python code
   - Pytest for automated testing
   - Node.js tests for bridge servers

4. **Agent Collaboration**
   - Ara (Grok.x.ai) maintains folder structure
   - Claude acts as copilot for code review
   - All agents work together without conflicts
   - Shared audit logging ensures coordination

## Features

### Live Alerts System 🚨

The platform includes a comprehensive real-time alert system for monitoring and responding to critical events:

**Backend Features:**
- WebSocket-based real-time alert delivery
- Multiple alert types: Info, Warning, Error, Security, System
- Alert severity levels: low, medium, high, critical
- Database persistence with SQLAlchemy
- RESTful API for alert management
- Integration with Piper TTS for audio notifications

**Frontend Features:**
- Real-time toast notifications for incoming alerts
- Slide-out Alert Center for viewing alert history
- Unread alert count badge in header
- Auto-reconnecting WebSocket connection
- Severity-based visual styling and animations
- Mark as read/dismiss functionality

**Security Alert Types:**
- `DEBUGGER_TOUCH` - Foreign debugger detection
- `CHAIN_BREAK` - Integrity failure events
- `LIE_DETECTED` - Truth probe violations
- `OVERRIDE_SPOKEN` - Forbidden command detection
- `YUVA9V_TRIPPED` - Emergency protocols activated

See [Piper Integration Documentation](docs/PIPER_INTEGRATION.md) for audio alert setup.

### EEG Streaming System 🧠

Real-time EEG biomedical signal acquisition and analysis via `eeg_streaming.py`:

- Lab Streaming Layer (LSL) inlet for hardware-agnostic EEG device support
- Band-power extraction: delta, theta, alpha, beta, gamma
- Butterworth bandpass filtering and Welch power spectral density
- Artifact detection and classification labeling
- Server-Sent Events (SSE) broadcasting for live dashboard streaming
- Thread-safe concurrent data store for polling endpoints

### Post-Quantum Authentication 🔐

`Backend_API_AUTH.py` implements quantum-resistant identity verification:

- **Dilithium2** post-quantum digital signatures (CRYSTALS-Dilithium)
- **TOTP** two-factor authentication as a second factor
- Signed JWT-style tokens using the authenticated public key
- Immutable audit log entries written to `/logs/auth.jsonl`
- `frontend/src/Frontend_src_Auth.jsx`: browser-side Dilithium signing via WebAssembly
- `frontend/src/xai_in_cert_Chain.html`: xAI certificate chain verification viewer

## Deployment

### Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Initialize the database
python scripts/init_db.py

# Test the alerts system
python scripts/test_alerts.py

# Run the backend server
cd backend
PYTHONPATH=.:./backend uvicorn app.main:app --reload
```


### Frontend Setup

```bash
# Install Node dependencies
cd frontend
npm install

# Set environment variables
echo "REACT_APP_API_URL=http://localhost:9899/api/v1" > .env
echo "REACT_APP_WS_URL=ws://localhost:9899" >> .env

# Run the development server
npm start
```


### Docker Deployment

```bash
# Build and deploy with Docker Compose
make build
make deploy
```


### Piper TTS Setup (Optional)

For audio alert notifications:

```bash
# Build Piper
cd piper-tts
make

# Download a voice model
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/voice-en-us-libritts-high.tar.gz
tar -xzf voice-en-us-libritts-high.tar.gz

# Set environment variable
export PIPER_MODEL_PATH=./voice-en-us-libritts-high.onnx
```


See [docs/PIPER_INTEGRATION.md](docs/PIPER_INTEGRATION.md) for detailed setup.

## Usage

### Creating Alerts via API

```bash
# Create a security alert
curl -X POST "http://localhost:9899/api/v1/alerts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "security",
    "title": "Unauthorized Access",
    "message": "Failed login attempt detected",
    "severity": "high",
    "source": "auth_system"
  }'

# Create an alert with audio notification
curl -X POST "http://localhost:9899/api/v1/alerts/?speak=true" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "critical",
    "title": "System Alert",
    "message": "Critical system failure detected",
    "severity": "critical"
  }'
```


### WebSocket Connection

The frontend automatically connects to the WebSocket endpoint for real-time alerts. To connect manually:

```javascript
const ws = new WebSocket('ws://localhost:9899/api/v1/alerts/ws/USER_ID');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received alert:', message);
};
```


## Testing

```bash
# Run backend tests
make test

# Run linter
make lint

# Clean up
make clean
```


## Execution and Chain Validation

Execution is controlled via the `./Ship` script, which performs:
- Hardware-backed commit sealing
- Chain validation (O-A-T-H)
- Federation checks across devices
- Divergence detection and halt on mismatch

## Access Control

- Root authority: Derek Appel
- Chain identifier: O-A-T-H
- Designated heir: DJ Appel

## License

GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007

Copyright (C) 2026 Appel420
