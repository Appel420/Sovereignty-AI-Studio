# Local collaboration and issue-suggestion flow

The active local collaboration boundary is:

```text
SGHv119 dashboard
    -> local bridge / local MCP
    -> local Bug Hunter and CodeMaster observations
    -> device-local deduplicated issue suggestions
    -> owner accepts, declines, defers, or resolves
    -> local CI verifies the selected change
```

No cloud agent, third-party issue service, or automatic GitHub issue creation is required.

## Issue suggestions

`local_governance/issue_suggestions.py` stores suggestions in a device-local JSONL file. Repeated observations use a stable fingerprint derived from:

- category;
- normalized reason;
- source;
- component;
- target;
- active mode.

Repeated observations increment `occurrences`, update `last_seen`, and append new evidence to the same suggestion. They do not create duplicate issues.

Suggestions require explicit owner action:

```text
PROPOSED -> ACCEPTED
PROPOSED -> DECLINED
PROPOSED -> DEFERRED
ACCEPTED -> RESOLVED
```

The store never contacts GitHub or a provider.

## Local CLI

```bash
python3 scripts/local_issue_suggestions.py --store state/issue-suggestions.jsonl list
python3 scripts/local_issue_suggestions.py --store state/issue-suggestions.jsonl decide <suggestion-id> ACCEPTED
```

The dashboard can use the same module through the local bridge/MCP adapter. The bridge should expose observations as Bug Hunter findings with exact component, target, evidence, and recommended action before any fix is offered.

## Verification

```bash
python3 -m pytest tests/test_issue_suggestions.py -q
```

The local MCP server remains read-only for workspace analysis. Applying an accepted fix belongs to the local agent branch and must be followed by local CI.
