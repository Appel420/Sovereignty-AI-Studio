"""Template Plugin — minimal example for the Sovereignty AI Studio Plugin SDK.

Copy this directory (``plugin_sdk/template_plugin/``) to create a new plugin.
Update ``plugin.json`` with your plugin's metadata, then implement your logic
inside the ``run`` function below.

The Plugin Agent will call ``run(task)`` with a task dict passed from the
event bus.  The function may be synchronous or async.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def run(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the plugin logic.

    Args:
        task: Arbitrary task payload from the event bus or gateway.

    Returns:
        Result dict that will be returned to the caller.
    """
    logger.info("Template plugin executed with task: %s", task)

    # ── Replace the example logic below with your own ──────────────────────
    action = task.get("action", "echo")
    data = task.get("data", "")

    if action == "echo":
        result = {"echo": data}
    elif action == "reverse":
        result = {"reversed": str(data)[::-1]}
    else:
        result = {"error": f"Unknown action '{action}'"}
    # ────────────────────────────────────────────────────────────────────────

    return {"plugin": "template_plugin", "result": result}
