# DevAssist420 ↔ SGHv119 integration contract

## Authority

`Appel420/Sovereign-DevAssist420` is the clean execution participant. `Appel420/Sovereignty-AI-Studio` is the presentation/control surface. The Studio must never become an authority source merely because it can call DevAssist.

The canonical sequence is:

`OWNER AUTHENTICATION → SESSION → PROPOSAL → POLICY/RISK REVIEW → OWNER CONFIRMATION → FOLD GRANT/REGRANT → FOLD AUTHORIZE_AND_COMMIT → EXECUTION → VERIFICATION → EVIDENCE`

DevAssist receives only already-authorized work. Its own repository explicitly defines the owner → policy → confirmation → Fold → operation boundary and rejects AI/MCP/provider authority delegation. 

## Stateful / stateless boundary

During an owner-authenticated session, the runtime may maintain transient task, proposal, and routing state required to complete the authorized operation.

At session close:

- capabilities are revoked;
- transient session state is destroyed;
- session identity is invalidated;
- only owner-approved persistent state and evidence may remain;
- the AI participant leaves with no authority.

Authentication is not authorization. Voice is not authorization. AI reasoning is not authorization.

## SGHv119 integration

The integration is deliberately attached to the existing `frontend/runtime/sghv119-bootstrap.js` boundary rather than duplicating control logic inside the monolithic HTML surface. SGHv119 already uses this bootstrap as its canonical runtime integration point.

`devassist420-integration.js` exposes only:

- status;
- owner-session open;
- proposal submission;
- execution using an explicit `AUTHORIZED` receipt;
- session close/revocation;
- voice-to-proposal conversion.

It does not implement Fold authority and does not accept a secret key.

## Transport

The browser adapter uses same-origin requests and refuses to operate outside a secure context. Production deployment is expected to remain HTTPS/WSS on the sovereign transport boundary; there is no external default endpoint and no silent cloud fallback.

## AI collaboration

Other models/agents are requesters. They can propose reasoning and work. They cannot grant, transfer, escalate, or inherit authority. A collaboration response must return through the same local authorization boundary before execution.

## Safety / risk disclosure

Consequential requests must identify the resource, operation, purpose, risks, rewards, and data boundary. Policy-denied resources must be denied without prompting. A negative Gate or Fold result is terminal for that operation.

## Evidence

The integration should emit auditable transitions for authentication, proposal, authorization, execution, verification, denial, quarantine, and session close. Cryptographic verification belongs to the evidence/verification plane; the browser adapter must not invent cryptographic authority.

## Repository separation

This integration does **not** import the legacy DevAssist420 Vercel/v0 React/TSX/Google-OAuth architecture. The clean DevAssist repository remains separate. Its documented integration target is Sovereignty-AI-Studio.
