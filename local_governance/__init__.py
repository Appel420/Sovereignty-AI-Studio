"""Device-local governance stores used by the integration plane."""

from .approvals import ApprovalStore
from .issue_suggestions import IssueSuggestionStore

__all__ = ["ApprovalStore", "IssueSuggestionStore"]
