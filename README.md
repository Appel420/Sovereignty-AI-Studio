# Sovereignty AI Studio

Private sovereign AI control surface for GitHub-coordinated agent work.

## Canonical UI

`SGHV119.html` is the primary interface.

The project does **not** use React as the sovereign runtime. The intended UI path is plain HTML, CSS, and JavaScript served from the repository or a local static server.

## Core Rule

All agent work runs through GitHub branches and reviewed pull requests.

| Branch | Agent | Provider | Role |
| --- | --- | --- | --- |
| `ara-hardened` | Ara / Grok | xAI | Security hardening |
| `claude` | Claude | Anthropic | Development |
| `gpt` | GPT / Codex | OpenAI | Architecture and verification |
| `copilot` | GitHub Copilot | GitHub | Code assistance |

The branch map is stored in:

```text
agent-workspaces.json
```

## Transport Policy

The default transport is **HTTP over TLS**.

Use:

```text
POST /ai/grok
POST /ai/claude
POST /ai/gpt
POST /ai/copilot
GET  /api/bridge/status
GET  /api/agents/status
```

Do **not** use insecure browser WebSockets as the default control channel.

WebSockets are only acceptable when all of the following are true:

1. The connection is `wss://`, not `ws://`.
2. TLS is enabled and verified.
3. The request is authenticated.
4. The server validates origin and authorization.
5. The feature explicitly requires bidirectional streaming.

For SGHV119, ordinary command and agent routing should stay request/response over HTTPS.

## Architecture

```text
Browser / iPhone
   |
   |-- HTTPS GET /SGHV119.html
   |
   |-- HTTPS POST /ai/:agentId
   |-- HTTPS GET  /api/bridge/status
   |-- HTTPS GET  /api/agents/status
        |
        v
   node-bridge / gateway
        |
        v
   internal services / GitHub agent workflow
```

## Repository Shape

```text
Sovereignty-AI-Studio/
├── SGHV119.html              # Main static sovereign control surface
├── agent-workspaces.json     # Agent-to-branch mapping
├── node-bridge/              # HTTP bridge and internal gateway routes
├── backend/                  # Internal API services
├── ai_core/                  # Core AI modules
├── agents/                   # Agent definitions
├── docs/                     # Documentation
└── README.md
```

## React Status

Legacy React files may still exist in the repository while cleanup is in progress. They are not the intended sovereign runtime and should not be treated as the canonical frontend.

The cleanup target is:

```text
SGHV119.html + HTTP bridge + GitHub branches
```

Not:

```text
React app + browser WebSocket control channel
```

## Local Start Pattern

Use the bridge/static server path that serves `SGHV119.html`, then verify health through HTTP:

```bash
curl /api/bridge/status
curl /api/agents/status
```

For local development without TLS, use loopback only. For device, LAN, or production access, terminate TLS and use HTTPS.

## Security Notes

- Do not commit API keys, OAuth secrets, certificates, or `.env` files.
- Keep `main` protected.
- Use pull requests for agent branch merges.
- Prefer short-lived tokens and least-privilege GitHub credentials.
- Use HTTPS for browser-to-bridge traffic.
- Avoid persistent socket channels unless they are authenticated `wss://` channels with origin enforcement.

## Current Operating Model

```text
SGHV119.html
   -> HTTPS request/response
   -> node bridge
   -> GitHub/agent workflow
   -> branch-specific pull request
```
