# Sovereignty AI Studio

[![CI](https://github.com/Appel420/Sovereignty-AI-Studio/workflows/CI/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions)
[![codecov](https://codecov.io/gh/Appel420/Sovereignty-AI-Studio/branch/main/graph/badge.svg)](https://codecov.io/gh/Appel420/Sovereignty-AI-Studio)

**Private Sovereign AI Research and Development Platform**  
**Core Model:** Super Grok Heavy 4.2  
(xAI) – Locked, Sealed, Sovereign  
**Authority:** Derek Appel  
**Last Updated:** March 15, 2026

## Overview

Sovereignty AI Studio is a fully private, self-contained research and production environment for advanced sovereign artificial intelligence systems.

The platform integrates specialized domains including computer vision, logical reasoning, biomedical signal processing, cryptographic vaulting, autonomous agents, and system orchestration. All components are designed for complete operational independence, end-to-end encryption, and tamper-resistant execution.

No external services, third-party models, or internet connectivity are required for core operation.

## Gateway & Ports

- **9898** — Node bridge gateway (only externally exposed entry point)
- **8000** — FastAPI backend (internal; proxied through `/api/v1` on the bridge)
- **8001** — Quart weather service (internal; proxied through `/api/weather` and `/api/forecast`)
- Docker Compose exposes only the node-bridge on 9898; backend, PostgreSQL, and Redis stay on the internal network (see `PORT_ALLOCATION.md` for details).

## Quick Start (local)

1. Install Python dependencies: `make install` (installs `requirements.txt` and `backend/requirements.txt`).
2. Install Node dependencies:
   - Root / unified server: `npm install`
   - Node bridge: `npm install --prefix node-bridge`
3. Start the backend API on 8000: `PYTHONPATH=./backend uvicorn app.main:app --reload --port 8000`
4. (Optional) Start the weather service on 8001: `PYTHONPATH=.:./backend hypercorn weather_dashboard:app --bind 0.0.0.0:8001`
5. Start the node bridge gateway on 9898: `npm --prefix node-bridge start` (proxies to the backend and weather services; WebSocket at `/ws/alerts`).
6. Run the WebSocket AI bridge when you need Claude/GPT/Grok routing: `node server_9898.js` (requires API keys in the environment).
7. All services together: `./start-all.sh` (starts weather dashboard, node bridge, and optional Redis if available).

## Project Structure

```
Sovereignty-AI-Studio/
├── backend/                 # FastAPI backend (port 8000, proxied through node-bridge)
├── node-bridge/             # Node gateway on 9898 (HTTP proxy + /ws/alerts)
├── server_9898.js           # AI agent WebSocket bridge (Claude/GPT/Grok)
├── unified_server.js        # Combined gateway/auth/agent server (port 9000, alias 9898/8443)
├── frontend/                # React TypeScript frontend
├── apps/                    # Dashboards and web utilities
├── ai_core/                 # Core AI modules and agents
├── resources/               # Assets, configs, and data
├── docs/                    # Documentation (port allocation, alerts, etc.)
├── scripts/                 # Deployment helpers (e.g., start-all.sh)
├── docker-compose.yml       # Builds backend + node-bridge; only 9898 is exposed
├── PORT_ALLOCATION.md       # Port map and routing expectations
└── README.md
```

## Key Components

- **src/agents/**: AI Agent Modules for various tasks including lie detection and EEG analysis
- **src/core/**: Core system files for the AI platform
- **src/security/**: Security and protection modules including live alerts and tamper detection
- **src/models/**: Machine learning models and quantum layers
- **src/utils/**: Utility functions and tools
- **apps/dashboards/**: Dashboard applications including post-quantum and EEG dashboards
- **apps/web/**: Web applications
- **ai_core/**: Core AI modules (lie detector, defense module, Ara core)
- **resources/**: Assets, configurations, and data files
- **scripts/**: Build and deployment scripts
- **crypto/**: Cryptography modules
- **backend/**: FastAPI backend with WebSocket support, REST API (12 endpoint groups), Piper TTS integration
- **frontend/**: React TypeScript frontend with real-time alert notifications and post-quantum auth UI
- **ios/**: iOS Swift Package (SovereigntyGuard) with debugger detection and audit logging
- **node-bridge/**: Node.js bridge connecting frontend, Python backends, and iSH/Code Pad
- **eeg_streaming.py**: Real-time EEG signal acquisition, band power analysis, and SSE broadcasting
- **Backend_API_AUTH.py**: Post-quantum authentication router using Dilithium2 signatures and TOTP
- **Harvard_Sentences.txt**: Standard phonetically balanced sentences for TTS voice evaluation
- **Piper TTS**: Piper text-to-speech integration for audio alerts (see [docs/PIPER_INTEGRATION.md](docs/PIPER_INTEGRATION.md))

## AI Agent Integration

Sovereignty AI Studio provides seamless integration with multiple AI agents, enabling you to connect with Claude, GPT, Grok, and GitHub Copilot in a unified, secure environment.

### Supported AI Agents

The platform integrates with four major AI providers through a WebSocket-based routing system:

1. **Claude (Anthropic)** - Claude Sonnet 4 via `api.anthropic.com`
2. **GPT (OpenAI)** - GPT-4o via `api.openai.com`
3. **Grok (xAI)** - Grok-2-latest via `api.x.ai`
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
│  │  WebSocket Bridge (Port 9898)      │                 │
│  │  server_9898.js / unified_server   │                 │
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
- Maximum prompt length: 1000 characters
- Maximum tokens per response: 1200
- Rate limiting: 30 messages/minute per connection
- Automatic API key validation
- Full audit logging for compliance

### Environment Setup

Create a `.env` file in the project root with your API keys and service ports:

```bash
# AI Agent API Keys
ANTHROPIC_API_KEY=sk-ant-...      # Required for Claude
OPENAI_API_KEY=sk-...              # Required for GPT
XAI_API_KEY=xai-...                # Required for Grok

# GitHub OAuth (for Copilot integration)
GH_CLIENT_ID=your_github_client_id
GH_CLIENT_SECRET=your_github_client_secret

# Ports and service URLs
NODE_BRIDGE_PORT=9898              # Only external port
BACKEND_URL=http://localhost:8000  # Proxied by node-bridge at /api/v1
WEATHER_URL=http://localhost:8001  # Proxied by node-bridge at /api/weather
CORS_ORIGIN=http://localhost:9898
PORT_UNIFIED=9000                  # Unified server port
PORT_BRIDGE=9898                   # Bridge alias for unified server
PORT_AUTH=8443                     # Auth alias for unified server
LOG_DIR=./logs                     # Audit log directory
VERBOSE=1                          # Enable verbose logging

# Docker users: point BACKEND_URL/WEATHER_URL to service names
# BACKEND_URL=http://backend:8000
# WEATHER_URL=http://backend:8001
```

**Security Notes:**
- Never commit API keys to version control
- Use `.gitignore` to exclude `.env` files
- Rotate keys regularly
- Monitor audit logs in `./logs/audit.jsonl`

### Gateway & Agent Servers

#### Node Bridge Gateway (`node-bridge/server.js`)
- Only exposed port (9898) for HTTP and WebSocket traffic.
- Proxies `/api/v1/*` → FastAPI backend (8000) and `/api/weather*` & `/api/forecast*` → Quart weather (8001).
- Real-time alerts over `ws://localhost:9898/ws/alerts`, `GET /health`, `GET /api/bridge/status`, and `POST /api/bridge/notify` for backend-to-frontend pushes.
- Install dependencies: `npm install --prefix node-bridge`
- Start: `npm --prefix node-bridge start`

#### WebSocket AI Bridge (`server_9898.js`)
- Handles `agent_request` → Claude/GPT/Grok with 30 msg/min rate limits and optional Piper TTS fallback.
- Uses environment keys `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, and `PIPER_*` paths if TTS is enabled.
- Install dependencies: `npm install`
- Start: `node server_9898.js`

#### Unified Server (`unified_server.js`)
- Combined gateway/auth/search/Piper + agent routing on port 9000 (aliases: 9898/8443).
- Install dependencies: `npm install`
- Start: `npm run start` (or `node unified_server.js`)

### GitHub Copilot Integration

GitHub Copilot is integrated via the GitHub OAuth workflow:

1. **Configure GitHub OAuth App**
   - Go to GitHub Settings → Developer Settings → OAuth Apps
   - Create a new OAuth App with callback URL: `http://localhost:9000/api/gh/callback`
   - Copy Client ID and Client Secret to `.env`

2. **Authenticate**
   ```bash
   # Start unified server
   node unified_server.js

   # Navigate to auth endpoint
   curl http://localhost:9000/api/gh/login
   ```

3. **Use Copilot Features**
   - Code suggestions in your IDE
   - Pull request summaries
   - Code review assistance

### Testing Agent Connections

Test your agent setup with the included test suite:

```bash
# Test agent routing
node --test test/server9898-agent-routing.test.js

# Test server endpoints
node --test test/server9898.test.js

# Run all server tests
npm test
```

**Example Test:**

```javascript
// Test Claude agent connection
const ws = new WebSocket('ws://localhost:9898');

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
   - Stay under 1000 characters for optimal performance
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
    const socket = new WebSocket('ws://localhost:9898');

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
        let url = URL(string: "ws://localhost:9898")!
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
    uri = "ws://localhost:9898"

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
echo "REACT_APP_API_URL=http://localhost:9898/api/v1" > .env
echo "REACT_APP_WS_URL=ws://localhost:9898" >> .env

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
curl -X POST "http://localhost:9898/api/v1/alerts/" \
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
curl -X POST "http://localhost:9898/api/v1/alerts/?speak=true" \
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
const ws = new WebSocket('ws://localhost:9898/api/v1/alerts/ws/USER_ID');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received alert:', message);
};
```

## Testing

```bash
# Install dependencies first
make install
npm install
npm install --prefix node-bridge

# Run backend tests (FastAPI + services)
make test

# Run linter
make lint

# Node bridge tests
npm --prefix node-bridge test

# Agent routing tests
node --test test/server9898-agent-routing.test.js
node --test test/server9898.test.js

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
