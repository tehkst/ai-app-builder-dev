from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base


PlatformBase = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class PlatformTenant(PlatformBase):
    __tablename__ = "platform_tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=True)
    status = Column(String, default="active", nullable=False)
    plan = Column(String, default="free", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformWorkspace(PlatformBase):
    __tablename__ = "platform_workspaces"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    owner_id = Column(String, nullable=True)
    status = Column(String, default="created", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformProject(PlatformBase):
    __tablename__ = "platform_projects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    project_id = Column(String, index=True, nullable=False)
    generation_status = Column(String, default="created", nullable=False)
    runtime_status = Column(String, default="not_run", nullable=False)
    deployment_status = Column(String, default="not_deployed", nullable=False)
    current_version = Column(Integer, default=1, nullable=False)
    generation_count = Column(Integer, default=0, nullable=False)
    repair_count = Column(Integer, default=0, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformGenerationRun(PlatformBase):
    __tablename__ = "platform_generation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    project_id = Column(String, index=True, nullable=False)
    status = Column(String, default="started", nullable=False)
    review_status = Column(String, nullable=True)
    runtime_status = Column(String, nullable=True)
    error_summary = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}", nullable=False)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


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

