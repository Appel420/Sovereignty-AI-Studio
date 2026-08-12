# Decision Log

Irreversible or cross-cutting decisions only.

## 2026-08-07

### Agent organization

**Decision:** Email, chat, and agent folders are reasoning and review records only.

**Authority:** Repository contracts, policy files, signed artifacts, and verified evidence.

### Hawking ownership validation

**Decision:** Ownership validation must verify canonical runtime modules independently from runner availability and incomplete dashboard migration.

**Reason:** Infrastructure availability must not masquerade as a code-correctness failure.

**Evidence:** Commit `4a166444fdfe82a36e3c00b34375d223c910c97e`.

### CI runner

**Decision:** Phone-only development uses GitHub-hosted ARM64 CI with `ubuntu-24.04-arm`.

**Reason:** iOS can trigger and inspect workflows but cannot provide a persistent GitHub self-hosted runner.

**Constraint:** Self-hosted runner policy remains documented separately until the owner decides whether to retire or restore that lane.

### Runtime authority

**Decision:** Runtime execution, policy resolution, integration evidence, and documentation remain separate control domains.

**Reason:** Connectors and dashboards observe and transport state; they do not become authority sources.

### ANE validation

**Decision:** CPU remains the correctness oracle. ANE execution requires numerical parity evidence before release status can be promoted.
