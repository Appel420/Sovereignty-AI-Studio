"""
Usage tracking model — records AI token consumption per user/org/provider.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(Integer, nullable=True, index=True)

    provider = Column(String(50), nullable=False, index=True)   # openai, anthropic, xai
    model = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)                # chat, generate, embed

    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    latency_ms = Column(Float, nullable=True)
    cost_usd = Column(Float, default=0.0)

    status = Column(String(20), default="success")             # success, error, timeout
    error_message = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=func.now(), index=True)
