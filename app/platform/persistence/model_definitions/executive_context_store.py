from sqlalchemy import Column, DateTime, Integer, String, Text

from app.platform.persistence.model_definitions.base import PlatformBase, utc_now


class PlatformContextStore(PlatformBase):
    __tablename__ = "platform_context_store"

    id = Column(Integer, primary_key=True)
    scope = Column(String(120), nullable=False, index=True)
    kind = Column(String(80), nullable=False, index=True)
    title = Column(String(240), nullable=False)
    body = Column(Text, nullable=False)
    source = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
