from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformAgentDefinition(PlatformBase):
    __tablename__ = "platform_agent_definitions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    capabilities_json = Column(Text, default="[]", nullable=False)
    risk_level = Column(String, default="medium", index=True, nullable=False)
    status = Column(String, default="active", index=True, nullable=False)
    source_approval_id = Column(String, index=True, nullable=True)
    source_type = Column(String, default="agent_factory", index=True, nullable=False)
    safe_mode = Column(Boolean, default=True, nullable=False)
    writes_code = Column(Boolean, default=False, nullable=False)
    requires_approval_for_new_tasks = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

class PlatformAgentTask(PlatformBase):
    __tablename__ = "platform_agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String, default="queued", index=True, nullable=False)
    priority = Column(String, default="normal", index=True, nullable=False)
    risk_level = Column(String, default="medium", index=True, nullable=False)

    task_type = Column(String, index=True, nullable=False)
    requested_by = Column(String, default="ai_agent", nullable=False)
    assigned_agent = Column(String, index=True, nullable=True)

    input_payload_json = Column(Text, default="{}", nullable=False)
    result_payload_json = Column(Text, default="{}", nullable=False)
    error_message = Column(Text, nullable=True)

    approval_required = Column(Boolean, default=False, nullable=False)
    approval_id = Column(String, index=True, nullable=True)

    parent_task_id = Column(String, index=True, nullable=True)
    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)

    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
