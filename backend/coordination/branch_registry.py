"""Authoritative agent branch registry.

This registry records delegated machine workspaces. It does not grant root
authority. Main and Collaboration remain owner-controlled integration targets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PROTECTED_BRANCHES: frozenset[str] = frozenset(
    {"Collaboration", "collaboration", "main", "master"}
)

OWNER_AUTHORIZED_OPERATIONS: frozenset[str] = frozenset(
    {"owner-approved merge", "owner-approved cherry-pick", "owner-authorized integration service"}
)


@dataclass(frozen=True, slots=True)
class BranchOwner:
    branch: str
    owner: str
    scope: frozenset[str]

    def allows(self, requested_scope: Iterable[str]) -> bool:
        requested = {str(item) for item in requested_scope}
        return not requested or requested.issubset(self.scope)


BRANCH_OWNERS: dict[str, BranchOwner] = {
    "copilot/main": BranchOwner("copilot/main", "GitHub Copilot", frozenset({"code-assistance", "fixes", "focused-fix"})),
    "Ara-hardened": BranchOwner("Ara-hardened", "Grok", frozenset({"security", "attestation", "hardening", "pqc"})),
    "GPT/Codex": BranchOwner("GPT/Codex", "ChatGPT / Codex", frozenset({"architecture", "integration", "verification"})),
    "DDG/DuckAI-main": BranchOwner("DDG/DuckAI-main", "DuckAI", frozenset({"research", "evidence", "sanitization"})),
    "claude": BranchOwner("claude", "Claude", frozenset({"implementation", "refactor"})),
    "DevAssist420": BranchOwner("DevAssist420", "DevAssist420", frozenset({"routing", "coordination"})),
    "sovereignty-ai": BranchOwner("sovereignty-ai", "Sovereignty AI", frozenset({"policy", "governance", "evidence"})),
    "family": BranchOwner("family", "Family Council", frozenset({"family", "usability", "sanitization"})),
    "owner": BranchOwner("owner", "Appel420", frozenset({"architecture", "approval", "ownership"})),
}


class BranchRegistry:
    def __init__(self, entries: dict[str, BranchOwner] | None = None) -> None:
        self._entries = dict(entries or BRANCH_OWNERS)

    def get(self, branch: str) -> BranchOwner | None:
        if branch in PROTECTED_BRANCHES:
            return None
        return self._entries.get(branch)

    def require(self, branch: str) -> BranchOwner:
        if branch in PROTECTED_BRANCHES:
            raise ValueError(f"Protected branch is not agent-writable: {branch}")
        owner = self._entries.get(branch)
        if owner is None:
            raise ValueError(f"Unknown agent branch: {branch}")
        return owner

    def is_writable(self, branch: str) -> bool:
        return branch not in PROTECTED_BRANCHES and branch in self._entries

    def is_owner_controlled(self, branch: str) -> bool:
        return branch in PROTECTED_BRANCHES

    def authorized_owner_operations(self) -> frozenset[str]:
        return OWNER_AUTHORIZED_OPERATIONS

    def branches(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def protected(self) -> frozenset[str]:
        return PROTECTED_BRANCHES
