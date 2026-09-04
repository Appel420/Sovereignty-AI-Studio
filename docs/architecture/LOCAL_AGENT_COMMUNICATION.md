# Local multi-agent communication contract

Agents communicate through `backend/coordination/local_agent_bus.py`.

```text
owner/device
    │ local Unix socket or in-process transport
    ▼
coordination bus
    ├── validates sender identity/provider/branch
    ├── validates repository and timestamp provenance
    ├── routes to the named recipient only
    ├── queues when recipient is offline
    └── never grants write authority
```

Each agent has its own development lane:

- Copilot: `copilot/*`
- GPT: `gpt/*`
- Grok: `grok/*`
- Claude: `claude/*`
- Ara: `ara/*`
- DevAssist420: `devassist420/*`

Agents may exchange task context, review requests, findings, and proposed patches
through the local bus. They may not write another agent's branch. Repository writes,
commits, pushes, merges, and promotion remain separate owner-approved operations.

The bus is deliberately not a cloud relay. Its transport description reports:

```json
{"network": false, "cloud": false, "repository_writes": false, "branch_writes": false}
```

The local MCP server remains read-only. It can expose workspace inspection and test
results to the owner-approved local client. A future patch/commit operation must use
the same lane validator plus an explicit owner approval bound to the exact request.
