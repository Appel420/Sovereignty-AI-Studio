"""Canonical local coordination contracts for DevAssist420 and the council."""
from .branch_registry import BRANCH_OWNERS, PROTECTED_BRANCHES, BranchOwner, BranchRegistry
from .compat import legacy_route_metadata
from .conflict_manager import ConflictManager, ConflictRecord, ScopeHold, scopes_overlap
from .council_result import CouncilResult
from .devassist_router import DevAssistRouter
from .task_envelope import TaskEnvelope

__all__ = [
    "BRANCH_OWNERS",
    "PROTECTED_BRANCHES",
    "BranchOwner",
    "BranchRegistry",
    "ConflictManager",
    "ConflictRecord",
    "ScopeHold",
    "CouncilResult",
    "DevAssistRouter",
    "TaskEnvelope",
    "legacy_route_metadata",
    "scopes_overlap",
]
