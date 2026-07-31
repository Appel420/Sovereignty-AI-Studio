"""Single local routing spine for DevAssist420 coordination tasks."""
from __future__ import annotations

from collections.abc import Iterable

from .branch_registry import BranchRegistry
from .conflict_manager import ConflictManager
from .council_result import CouncilResult
from .lease import LeaseError, LeaseIssuer
from .task_envelope import TaskEnvelope


class DevAssistRouter:
    """Classify once, route once, issue lease, preserve parallel work safely."""

    _SCOPE_BRANCHES = (
        (("security", "attestation", "hardening", "pqc"), "ara-hardened"),
        (("policy", "governance", "evidence"), "sovereignty-ai"),
        (("routing", "coordination"), "devassist420"),
        (("family", "usability", "sanitization"), "family"),
        (("implementation", "refactor"), "claude"),
        (("architecture", "integration", "verification"), "gpt"),
        (("code-assistance", "fixes", "focused-fix"), "copilot"),
    )

    def __init__(
        self,
        registry: BranchRegistry | None = None,
        conflicts: ConflictManager | None = None,
        leases: LeaseIssuer | None = None,
    ) -> None:
        self.registry = registry or BranchRegistry()
        self.conflicts = conflicts or ConflictManager()
        self.leases = leases or LeaseIssuer()

    def classify(
        self,
        *,
        task_id: str,
        requester: str,
        owner: str,
        scope: Iterable[str],
        requested_agent: str | None = None,
        branch: str | None = None,
        mode: str = "offline",
        requires_owner_approval: bool = False,
        parallel_group: str | None = None,
    ) -> TaskEnvelope:
        normalized_scope = tuple(dict.fromkeys(str(item) for item in scope))
        selected_branch = branch or self._select_branch(normalized_scope, requested_agent)
        self.registry.require(selected_branch)
        selected_owner = self.registry.require(selected_branch)
        if not selected_owner.allows(normalized_scope):
            raise ValueError(
                f"Branch {selected_branch!r} does not own requested scope {normalized_scope!r}"
            )
        return TaskEnvelope(
            task_id=task_id,
            requester=requester,
            owner=owner,
            requested_agent=requested_agent,
            branch=selected_branch,
            scope=normalized_scope,
            mode=mode,
            requires_owner_approval=requires_owner_approval,
            parallel_group=parallel_group,
        )

    def route(self, envelope: TaskEnvelope) -> CouncilResult:
        if envelope.branch is None:
            return CouncilResult.denied("No branch was selected")
        if not self.registry.is_writable(envelope.branch):
            return CouncilResult.denied(
                f"Protected or unknown branch is not agent-writable: {envelope.branch}"
            )
        branch_owner = self.registry.require(envelope.branch)
        conflict = self.conflicts.register(envelope)
        if conflict is not None:
            return CouncilResult(
                approved=False,
                conflicts=(conflict,),
                notes=("Overlapping work is held for council review; no files were changed.",),
            )
        try:
            token = self.leases.issue(envelope, agent_id=branch_owner.owner)
        except LeaseError as exc:
            self.conflicts.release(envelope.task_id)
            return CouncilResult.denied(f"lease issuance failed: {exc}")
        return CouncilResult.route_for(branch_owner, envelope.scope, lease=token)

    def require_write(self, lease_token, paths: Iterable[str]):
        """I9 gate — call before any repository mutation."""
        return self.leases.require_for_write(lease_token, paths)

    def release(self, task_id: str) -> None:
        self.leases.release_task(task_id)
        self.conflicts.release(task_id)

    @staticmethod
    def _select_branch(scope: tuple[str, ...], requested_agent: str | None) -> str:
        if requested_agent:
            requested = requested_agent.lower()
            aliases = {"ara": "ara-hardened", "grok": "ara-hardened", "sovereignty": "sovereignty-ai"}
            return aliases.get(requested, requested)
        scope_set = set(scope)
        for keywords, branch in DevAssistRouter._SCOPE_BRANCHES:
            if scope_set.intersection(keywords):
                return branch
        return "devassist420"
