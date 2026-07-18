from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformOperationalEvidence(PlatformBase):
    __tablename__ = "platform_operational_evidence"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String, unique=True, index=True, nullable=False)
    evidence_type = Column(String, index=True, nullable=False)
    authority = Column(String, index=True, nullable=False)
    scope = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    payload_json = Column(Text, default="{}", nullable=False)
    observed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
