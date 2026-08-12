# Air-gapped tool execution and sabotage scanning

The tool dispatcher is deliberately fail-closed. It allows only read-oriented,
workspace-scoped tools (`cat`, `echo`, `grep`, and `ls`). It does not enable an
arbitrary agent toolset, shell execution, interpreters, `sudo`, `rm -rf`, network
clients, or automatic fixes.

AI-generated tool requests are data until the local dispatcher validates them.
A model never executes commands directly. The dispatcher validates the tool,
arguments, workspace, timeout, and output size before invoking a process with
`shell=False`.

The sabotage scanner is report-only. It detects selected high-risk patterns and
never modifies files. Any future autofix capability must require a separate
owner-approved mutation, backup/quarantine, diff review, and local test run.

Use the implementation from Python with an explicit approved workspace:

```python
from pathlib import Path
from sovereignty_policy.infrastructure.tool_executor import execute_tool_call

print(execute_tool_call("echo", ["air-gapped execution successful"], workspace=Path(".")))
```
