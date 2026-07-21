from app.platform.persistence.model_definitions.base import (
    Column,
    DateTime,
    Integer,
    PlatformBase,
    String,
    Text,
    utc_now,
)


class PlatformOrganizationalEvent(PlatformBase):
    """Durable, replay-safe reference to a canonical platform fact."""

    __tablename__ = "platform_organizational_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    source = Column(String, index=True, nullable=False)
    source_authority = Column(String, index=True, nullable=False)
    aggregate_type = Column(String, index=True, nullable=False)
    aggregate_id = Column(String, index=True, nullable=False)
    schema_version = Column(String, nullable=False)
    correlation_id = Column(String, index=True, nullable=True)
    causation_id = Column(String, index=True, nullable=True)
    actor = Column(String, nullable=False)
    evidence_references_json = Column(Text, default="[]", nullable=False)
    payload_json = Column(Text, default="{}", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
