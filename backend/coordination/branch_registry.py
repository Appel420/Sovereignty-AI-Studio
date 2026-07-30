"""Authoritative agent branch registry.

The registry describes ownership and permitted scopes; it does not grant root
authority. Integration into ``main`` always remains an owner-approved action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class BranchOwner:
    branch: str
    owner: str
    scope: frozenset[str]

    def allows(self, requested_scope: Iterable[str]) -> bool:
        requested = {str(item) for item in requested_scope}
        return not requested or requested.issubset(self.scope)


BRANCH_OWNERS: dict[str, BranchOwner] = {
    "ara-hardened": BranchOwner("ara-hardened", "Ara", frozenset({"security", "attestation", "hardening"})),
    "claude": BranchOwner("claude", "Claude", frozenset({"implementation", "refactor"})),
    "gpt": BranchOwner("gpt", "GPT", frozenset({"architecture", "integration", "verification"})),
    "copilot": BranchOwner("copilot", "GitHub Copilot", frozenset({"code-assistance", "fixes"})),
    "devassist420": BranchOwner("devassist420", "DevAssist420", frozenset({"routing", "coordination"})),
    "sovereignty-ai": BranchOwner("sovereignty-ai", "Sovereignty AI", frozenset({"policy", "governance", "evidence"})),
    "family": BranchOwner("family", "Family Council", frozenset({"family", "usability", "sanitization"})),
    "owner": BranchOwner("owner", "Appel420", frozenset({"architecture", "approval", "ownership"})),
}


class BranchRegistry:
    def __init__(self, entries: dict[str, BranchOwner] | None = None) -> None:
        self._entries = dict(entries or BRANCH_OWNERS)

    def get(self, branch: str) -> BranchOwner | None:
        return self._entries.get(branch)

    def require(self, branch: str) -> BranchOwner:
        owner = self.get(branch)
        if owner is None:
            raise ValueError(f"Unknown agent branch: {branch}")
        return owner

    def branches(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))
