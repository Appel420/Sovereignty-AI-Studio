"""
Plugin / Agent marketplace model.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class Plugin(Base):
    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)

    # Python import path: e.g. "plugins.examples.example_chat_plugin:ExampleChatPlugin"
    entry_point = Column(String(500), nullable=False)

    config_schema = Column(JSON, nullable=True)    # JSON Schema for plugin config
    default_config = Column(JSON, nullable=True)

    status = Column(String(50), default="inactive", index=True)  # active, inactive, error
    is_system = Column(Boolean, default=False)     # Built-in vs user-installed
    is_enabled = Column(Boolean, default=False)

    installed_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(50), nullable=True)
