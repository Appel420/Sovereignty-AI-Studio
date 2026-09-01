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
