from dataclasses import dataclass


@dataclass(frozen=True)
class Grant:
    subject: str
    branch: str
    granted_by: str
    expires_at: int | None = None
    revoked: bool = False


def can_hydrate(grant: Grant, subject: str, branch: str, now: int) -> bool:
    if grant.subject != subject or grant.branch != branch:
        return False
    if grant.revoked:
        return False
    if grant.expires_at is not None and now >= grant.expires_at:
        return False
    return True


def test_expired_grant_denied():
    grant = Grant("user", "main", "owner", expires_at=100)
    assert not can_hydrate(grant, "user", "main", 100)


def test_revoked_grant_denied():
    grant = Grant("user", "main", "owner", revoked=True)
    assert not can_hydrate(grant, "user", "main", 1)


def test_unauthorized_subject_or_branch_denied():
    grant = Grant("user", "main", "owner")
    assert not can_hydrate(grant, "other", "main", 1)
    assert not can_hydrate(grant, "user", "other", 1)


def test_context_cannot_change_authorization():
    grant = Grant("user", "main", "owner")
    result = can_hydrate(grant, "user", "main", 1)
    assert result is True
    assert can_hydrate(grant, "user", "other", 1) is False
