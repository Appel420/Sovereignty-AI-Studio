from datetime import datetime, timedelta, timezone

from backend.coordination.workflow_authorization import (
    ALLOW, DENY, UNKNOWN, AuthenticatedOwner, DecisionCode, ReplayStore,
    ScreenState, WorkflowAuthorizationService, WorkflowEnvelope,
)

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def env(**changes):
    values = dict(version="1.0", workflow_id="wf-1", issuer="device-owner", device_id="device-root-001", action="branch-write", target="local-runtime", scope=("backend/coordination",), branch="copilot/main", created_at=(NOW - timedelta(minutes=1)).isoformat(), expires_at=(NOW + timedelta(minutes=10)).isoformat(), nonce="nonce-1", sequence_number=1, signature="signed-envelope")
    values.update(changes)
    return WorkflowEnvelope(**values)


def owner():
    return AuthenticatedOwner("Appel420", "device-root-001", "local-session-1", True, NOW.isoformat())


def auth(audit, **kwargs):
    return WorkflowAuthorizationService(device_registered=lambda _: kwargs.get("registered", True), verify_signature=lambda _: kwargs.get("signature", True), policy_allows=lambda _: kwargs.get("policy", True), audit_append=audit.append, owner_login="Appel420", replay_store=kwargs.get("replay") or ReplayStore(), now=lambda: NOW)


def test_recognized_owner_allows_local_workflow():
    audit_log = []
    result = auth(audit_log).authorize(env(), owner=owner())
    assert result.decision == ALLOW
    assert result.code == DecisionCode.ALLOWED
    assert result.capability is None


def test_wrong_login_locks_without_cloud_handoff():
    audit_log = []
    wrong = AuthenticatedOwner("other-user", "device-root-001", "s", True, NOW.isoformat())
    result = auth(audit_log).authorize(env(), owner=wrong)
    assert result.decision == DENY
    assert result.code == DecisionCode.OWNER_SESSION_MISMATCH
    assert result.screen_state == ScreenState.LOCKED
    assert result.evidence["data_sent"] is False


def test_signature_valid_is_not_authorization():
    audit_log = []
    result = auth(audit_log, policy=False).authorize(env(), owner=owner())
    assert result.decision == DENY
    assert result.code == DecisionCode.POLICY_DENIED


def test_unknown_device_is_denied_and_locked():
    audit_log = []
    result = auth(audit_log, registered=False).authorize(env(), owner=owner())
    assert result.decision == DENY
    assert result.code == DecisionCode.DEVICE_NOT_REGISTERED
    assert result.screen_state == ScreenState.LOCKED


def test_replay_is_denied():
    audit_log = []
    replay = ReplayStore()
    service = auth(audit_log, replay=replay)
    assert service.authorize(env(), owner=owner()).decision == ALLOW
    assert service.authorize(env(), owner=owner()).code == DecisionCode.REPLAYED_REQUEST


def test_external_requires_explicit_owner_approval_and_retention():
    audit_log = []
    result = auth(audit_log).authorize(env(target="github", action="create_pull_request"), owner=owner(), execution_target="external", state_permission="explicit_files", retention_permission="declared", owner_confirmation=False)
    assert result.decision == DENY
    assert result.code == DecisionCode.OWNER_SESSION_REQUIRED


def test_approved_external_capability_is_scoped():
    audit_log = []
    result = auth(audit_log).authorize(env(target="github", action="create_pull_request"), owner=owner(), execution_target="external", state_permission="explicit_files", retention_permission="declared", owner_confirmation=True)
    assert result.decision == ALLOW
    assert result.capability is not None
    assert result.capability.destination == "github"
    assert result.capability.action == "create_pull_request"


def test_audit_failure_returns_unknown():
    def fail(_event):
        raise OSError("ledger unavailable")
    service = WorkflowAuthorizationService(device_registered=lambda _: True, verify_signature=lambda _: True, policy_allows=lambda _: True, audit_append=fail, owner_login="Appel420", now=lambda: NOW)
    result = service.authorize(env(), owner=owner())
    assert result.decision == UNKNOWN
    assert result.code == DecisionCode.AUDIT_UNAVAILABLE
