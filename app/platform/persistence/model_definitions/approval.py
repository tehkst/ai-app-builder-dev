from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformApprovalRequest(PlatformBase):
    __tablename__ = "platform_approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    approval_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending", index=True, nullable=False)
    risk_level = Column(String, default="medium", index=True, nullable=False)
    requested_by = Column(String, default="ai_agent", nullable=False)
    approver_id = Column(String, nullable=True)
    source_type = Column(String, index=True, nullable=True)
    source_id = Column(String, index=True, nullable=True)
    action_type = Column(String, nullable=True)
    action_payload_json = Column(Text, default="{}", nullable=False)
    decision_note = Column(Text, nullable=True)
    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    chat_channel = Column(String, nullable=True)
    chat_message_id = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

class PlatformAuditEvent(PlatformBase):
    __tablename__ = "platform_audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)
    actor_type = Column(String, default="unknown", nullable=False)
    actor_id = Column(String, nullable=True)
    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    status = Column(String, index=True, nullable=False)
    route = Column(String, nullable=True)
    auth_mode = Column(String, nullable=True)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
