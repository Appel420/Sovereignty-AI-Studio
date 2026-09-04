"""Lane map and provenance contract for owner-controlled collaboration."""
from __future__ import annotations

from datetime import datetime, timezone


CURRENT_PROVENANCE = {
    "human_authority": "Appel420",
    "machine_agent": "GitHub Copilot",
    "agent_id": "copilot",
    "provider_path": "github-copilot",
    "model_id": "5.6",
    "repository": "Appel420/Sovereignty-AI-Studio",
    "branch": "copilot/main",
}


def current_provenance() -> dict[str, str]:
    value = dict(CURRENT_PROVENANCE)
    value["timestamp"] = datetime.now(timezone.utc).isoformat()
    return value
