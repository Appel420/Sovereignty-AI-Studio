      codex/devassist420-sghv119-integration
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

# Sovereign DevAssist420 / SGHv119 integration

This integration keeps DevAssist420 separate from the Studio repository while making SGHv119 its human-visible control surface.

## Boundary

`SGHv119.html` → `sghv119-bootstrap.js` → `devassist420-bridge.js` → local DevAssist service → Human/Policy Gate → FoldAuthority → execution.

The browser adapter is deliberately **not** an authority source. It cannot grant capabilities, manufacture a Fold capability, or bypass owner authentication.

## Required sequence

1. Authenticate the device owner/session.
2. Evaluate policy and resource authority.
3. Present risk, reward, pros, and cons for consequential requests.
4. Obtain explicit owner confirmation where required.
5. Map the successful gate result to the exact Fold `subject/object/operation/epoch` tuple.
6. Call Fold `grant` or `regrant`.
7. Only after Fold success may DevAssist execute or instantiate a model.
8. Every consequential execution remains bound to the capability/session/epoch and uses Fold `authorize_and_commit`.
9. Verification failure, authorization denial, malformed authorization output, or unavailable authority fails closed.

## Resource governance

Services, files, repositories, model providers, AI peers, network endpoints, and device capabilities must be represented as resources with explicit policy state. A resource may be `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`; absence of a trustworthy decision is not permission.

## State and session semantics

Owner-approved persistent state remains in the owner-controlled local state store. Transient reasoning/tool/session state is session-scoped and must be destroyed or invalidated at close. AI collaborators receive no continuing authority merely because a session existed.

## Voice

Voice is an input channel only. Wake-word or speech recognition may create a request, but it does not create authority. The request follows the same owner authentication, risk disclosure, confirmation, Gate, Fold, and evidence chain.

## AI collaboration

AI-to-AI traffic is advisory/request-response collaboration. A peer may propose work or request a capability. It cannot authorize itself, delegate its authority, or silently forward a capability to another peer.

## Evidence

The integration should emit evidence for authorization decisions, Fold grant/regrant outcomes, execution, verification, and session close. Evidence must be treated as data by SGHv119; never render untrusted evidence through `innerHTML`.

## Frontend constraint

The clean DevAssist420 integration does not introduce React, TSX, JSX, Vercel, v0.dev, or Google OAuth routing. Those belong to the legacy implementation and remain separate.