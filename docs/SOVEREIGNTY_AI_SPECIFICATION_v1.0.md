# Sovereignty AI Specification v1.0

**Status:** Normative Architecture Specification  
**Authority:** Human Owner  
**Default Mode:** Offline  
**Default Decision:** Deny  
**Execution:** Self-hosted Linux runner and device-local services  
**Canonical API spelling:** `SCARLedger`

## Local-first rule

Local and offline operation is the primary supported operating mode. Core startup, dashboard navigation, local bridges, local cache, audit, tests, and diagnostics SHALL work without cloud services, hosted runners, provider APIs, SaaS scanners, remote agents, container registries, CDNs, or external network access.

Cloud, provider, and external-network capabilities are optional extensions only. They require explicit owner approval, policy authorization, an allowlisted destination, and local audit evidence. They must never be required for the default runtime or for local validation. If an optional external capability is unavailable, the platform preserves safe local functionality and fails closed for that capability.

The canonical CI environment is the repository's self-hosted Linux runner. GitHub-hosted runners and cloud artifact services are not part of the required execution path.

## Part I — Normative Requirements

### 1. Authority Model

1. The device owner is the only Root Authority.
2. AI participants are advisory by default.
3. Authority cannot be delegated implicitly.
4. No AI participant, provider, service, or repository may grant itself authority, modify Root Authority, or change policy without explicit owner authorization.
5. Credential possession does not imply permission.
6. Sensitive actions require a scoped capability with an owner decision, intended purpose, scope, expiry, and audit identity.

### 2. Network and service boundaries

- Bind local services to loopback by default.
- Use `127.0.0.1:9897` for the Python bridge, `127.0.0.1:9898` for the dashboard, and `127.0.0.1:9899` for the Node bridge.
- Do not initialize provider adapters, cloud clients, external polling, WebSockets, credential consumers, or remote agents before `PolicyEngine` succeeds.
- Do not add a mandatory cloud dependency to local functionality.
- Do not upload source, private payloads, credentials, reasoning text, or telemetry by default.

### 3. Canonical Runtime State

Canonical Runtime State is always required. Missing, invalid, stale, or unverifiable state is a threat condition. The platform SHALL fail closed, record local evidence, alert the owner when possible, and deny provider, credential, mission, and external-network capabilities.

### 4. Evidence Requirements

Every policy-relevant action SHALL produce append-only local `SCARLedger` evidence. Credentials, session keys, raw private payloads, and secrets SHALL never be recorded.

### 5. Failure Handling

Failures SHALL be deterministic. The platform SHALL deny the affected capability, preserve cached local functionality where safe, and avoid automatic escalation. Optional external-service failures must not prevent local startup or local tests.

## Local validation acceptance criteria

- The workflow runs on a self-hosted Linux runner.
- The workflow does not require a cloud runner, cloud scanner, registry login, or remote artifact upload.
- Python, Node, shell, and project tests run against locally installed tools.
- The incomplete SCAR patch is documentation and is not linted as runtime Python.
- `SG_NETWORK_MODE=offline` prevents external access from being treated as a startup requirement.
- The dashboard and local bridges remain loopback-only by default.
