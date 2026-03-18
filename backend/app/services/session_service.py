"""
Session management service — create, validate, and revoke user sessions.
"""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.session import UserSession


SESSION_TTL_HOURS = 24


def create_session(
    db: Session,
    user_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    data: Optional[dict] = None,
    ttl_hours: int = SESSION_TTL_HOURS,
) -> UserSession:
    token = secrets.token_urlsafe(48)
    session = UserSession(
        session_token=token,
        user_id=user_id,
        data=json.dumps(data or {}),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, token: str) -> Optional[UserSession]:
    return (
        db.query(UserSession)
        .filter(
            UserSession.session_token == token,
            UserSession.is_active.is_(True),
        )
        .first()
    )


def validate_session(db: Session, token: str) -> Optional[UserSession]:
    """Return the session if it exists and is not expired."""
    session = get_session(db, token)
    if not session:
        return None
    if session.expires_at < datetime.utcnow():
        session.is_active = False
        db.commit()
        return None
    session.last_accessed_at = datetime.utcnow()
    db.commit()
    return session


def revoke_session(db: Session, token: str) -> bool:
    session = get_session(db, token)
    if not session:
        return False
    session.is_active = False
    db.commit()
    return True


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    """Revoke all active sessions for a user. Returns count revoked."""
    count = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.is_active.is_(True))
        .update({"is_active": False})
    )
    db.commit()
    return count


def get_active_sessions(db: Session, user_id: int) -> list:
    return (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.is_active.is_(True),
            UserSession.expires_at > datetime.utcnow(),
        )
        .order_by(UserSession.last_accessed_at.desc())
        .all()
    )
