#!/usr/bin/env python3
"""
agent_lane.py — enforces which paths in the family tree each AI agent is
allowed to write to. This reuses the same scope-overlap logic proven
earlier in lease.py, applied to a durable approval model instead of a
transient lock:

  - Agent's write falls within its approved lane -> commits directly to
    the shared branch (or logs to family/models/ as usual).
  - Agent's write falls OUTSIDE its approved lane -> the content is
    written to pending-approvals/<request-id>/ as an inert proposal.
    Nothing in the real tree changes. The agent's job, at that point,
    is done — it waits. A human runs approve.py or deny.py.

No agent can bypass this by choosing a different tool or retrying —
every write in this system is required to go through here first.
"""
from __future__ import annotations

import os
import sys
import json
import uuid
import subprocess
import datetime


def scopes_overlap(scope_a: list[str], scope_b: list[str]) -> bool:
    def norm(p):
        return p.rstrip("/")
    for a in scope_a:
        na = norm(a)
        for b in scope_b:
            nb = norm(b)
            if na == nb or na.startswith(nb + "/") or nb.startswith(na + "/"):
                return True
    return False


# Each agent's approved lane. Extend this as you approve new agents/scopes —
# this file itself should only be editable by the human owner, not by any
# agent (enforce that at the filesystem level: chmod 644, owned by you).
APPROVED_LANES = {
    "claude": ["family/models/anthropic/"],
    "gpt": ["family/models/openai/"],
    "grok": ["family/models/xai/"],
    "copilot": ["family/models/github/"],
}


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def request_write(repo_path: str, agent: str, target_path: str, content: str, reason: str) -> dict:
    """The single entry point every agent write must go through."""
    lane = APPROVED_LANES.get(agent, [])
    in_lane = scopes_overlap(lane, [target_path])

    if in_lane:
        full_path = os.path.join(repo_path, target_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        run(["git", "checkout", "-q", "shared"], cwd=repo_path)
        run(["git", "add", target_path], cwd=repo_path)
        run(["git", "commit", "-q", "-m", f"[{agent}] {reason}"], cwd=repo_path)
        return {"status": "applied", "agent": agent, "path": target_path}

    # Out of lane: queue it, touch nothing real.
    request_id = str(uuid.uuid4())[:8]
    queue_dir = os.path.join(repo_path, "pending-approvals", request_id)
    os.makedirs(queue_dir, exist_ok=True)
    with open(os.path.join(queue_dir, "content.txt"), "w") as f:
        f.write(content)
    with open(os.path.join(queue_dir, "request.json"), "w") as f:
        json.dump({
            "request_id": request_id,
            "agent": agent,
            "requested_path": target_path,
            "reason": reason,
            "requested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "approved_lane_for_agent": lane,
            "status": "pending",
        }, f, indent=2)

    return {"status": "pending_approval", "agent": agent, "request_id": request_id,
             "path": target_path, "reason": f"'{target_path}' is outside {agent}'s approved lane {lane}"}


def list_pending(repo_path: str) -> list[dict]:
    base = os.path.join(repo_path, "pending-approvals")
    out = []
    for entry in sorted(os.listdir(base)):
        req_file = os.path.join(base, entry, "request.json")
        if os.path.isfile(req_file):
            with open(req_file) as f:
                out.append(json.load(f))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print('usage: agent_lane.py <repo-path> <agent> <target-path> <content> "<reason>"')
        sys.exit(1)
    result = request_write(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    print(json.dumps(result, indent=2))
