"""
Audit log model — immutable record of all critical system actions.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)   # denormalized snapshot

    action = Column(String(100), nullable=False, index=True)   # e.g. user.login, ai.chat
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)

    # Serialized extra context (JSON string)
    details = Column(Text, nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), default="success")             # success, failure

    created_at = Column(DateTime, default=func.now(), index=True)
