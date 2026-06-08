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


class PlatformGeneratedFile(PlatformBase):
    __tablename__ = "platform_generated_files"

    id = Column(Integer, primary_key=True, index=True)
    generated_file_id = Column(String, unique=True, index=True, nullable=False)

    workflow_run_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    project_id = Column(String, index=True, nullable=True)

    source_step_id = Column(String, index=True, nullable=True)
    source_agent_id = Column(String, index=True, nullable=True)

    path = Column(String, index=True, nullable=False)
    language = Column(String, nullable=True)
    purpose = Column(Text, nullable=True)

    content_preview = Column(Text, default="", nullable=False)
    content_hash = Column(String, index=True, nullable=False)

    write_status = Column(String, default="persisted_preview", index=True, nullable=False)
    rollback_status = Column(String, default="not_required", index=True, nullable=False)

    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformMaterializationApprovalRecord(PlatformBase):
    __tablename__ = "platform_materialization_approval_records"

    id = Column(Integer, primary_key=True, index=True)
    materialization_approval_record_id = Column(String, unique=True, index=True, nullable=False)

    generated_file_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)

    selected_path = Column(String, index=True, nullable=True)
    approval_status = Column(String, default="approved", index=True, nullable=False)
    approval_action = Column(String, default="approve", index=True, nullable=False)
    approval_token = Column(String, index=True, nullable=True)
    approved_by = Column(String, default="platform_admin", nullable=False)
    approval_reason = Column(Text, nullable=True)

    safety_mode = Column(String, default="persistent_record_only_no_write_capability", index=True, nullable=False)
    approval_record_only = Column(Boolean, default=True, nullable=False)
    approval_grants_filesystem_write_capability = Column(Boolean, default=False, nullable=False)
    materialization_execution_enabled = Column(Boolean, default=False, nullable=False)
    generated_files_written_to_disk = Column(Boolean, default=False, nullable=False)
    filesystem_write_performed = Column(Boolean, default=False, nullable=False)
    disk_write_performed = Column(Boolean, default=False, nullable=False)
    runtime_server_started = Column(Boolean, default=False, nullable=False)
    preview_server_started = Column(Boolean, default=False, nullable=False)
    generated_code_execution_performed = Column(Boolean, default=False, nullable=False)
    repair_applied = Column(Boolean, default=False, nullable=False)
    restore_executed = Column(Boolean, default=False, nullable=False)

    metadata_json = Column(Text, default="{}", nullable=False)
    approved_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformRuntimeApprovalRecord(PlatformBase):
    __tablename__ = "platform_runtime_approval_records"

    id = Column(Integer, primary_key=True, index=True)
    runtime_approval_record_id = Column(String, unique=True, index=True, nullable=False)

    workflow_run_id = Column(String, index=True, nullable=True)
    selected_generated_file_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)

    approval_status = Column(String, default="approved", index=True, nullable=False)
    approval_action = Column(String, default="approve", index=True, nullable=False)
    approval_token = Column(String, index=True, nullable=True)
    approved_by = Column(String, default="platform_admin", nullable=False)
    approval_reason = Column(Text, nullable=True)

    run_plan_status = Column(String, index=True, nullable=True)
    framework_type = Column(String, index=True, nullable=True)
    working_directory = Column(String, nullable=True)
    run_command = Column(String, nullable=True)
    install_command = Column(String, nullable=True)
    runtime_port = Column(Integer, nullable=True)

    safety_mode = Column(String, default="runtime_approval_gate_only_no_execution", index=True, nullable=False)
    approval_record_only = Column(Boolean, default=True, nullable=False)
    runtime_execution_enabled = Column(Boolean, default=False, nullable=False)
    install_packages_performed = Column(Boolean, default=False, nullable=False)
    runtime_server_started = Column(Boolean, default=False, nullable=False)
    preview_server_started = Column(Boolean, default=False, nullable=False)
    generated_code_execution_performed = Column(Boolean, default=False, nullable=False)
    node_command_executed = Column(Boolean, default=False, nullable=False)
    python_command_executed = Column(Boolean, default=False, nullable=False)
    generated_files_written = Column(Boolean, default=False, nullable=False)
    filesystem_write_performed = Column(Boolean, default=False, nullable=False)
    disk_write_performed = Column(Boolean, default=False, nullable=False)
    repair_applied = Column(Boolean, default=False, nullable=False)
    restore_executed = Column(Boolean, default=False, nullable=False)

    metadata_json = Column(Text, default="{}", nullable=False)
    approved_at = Column(DateTime(timezone=True), default=utc_now, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformGeneratedFileRestoreExecution(PlatformBase):
    __tablename__ = "platform_generated_file_restore_executions"

    id = Column(Integer, primary_key=True, index=True)
    restore_execution_id = Column(String, unique=True, index=True, nullable=False)

    approval_id = Column(String, index=True, nullable=True)
    target_version_id = Column(String, index=True, nullable=True)
    generated_file_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)

    restore_status = Column(String, default="pending", index=True, nullable=False)
    restore_action = Column(String, default="restore_to_version", index=True, nullable=False)
    restore_reason = Column(Text, nullable=True)
    restore_requested_by = Column(String, default="platform_admin", nullable=False)

    safety_mode = Column(String, default="safe_db_restore_execution_only", index=True, nullable=False)
    restore_source = Column(String, default="db_version_snapshot", nullable=False)
    restore_target = Column(String, default="db_preview_content", nullable=False)

    target_version_number = Column(Integer, nullable=True)
    source_content_hash = Column(String, nullable=True)
    restored_content_hash = Column(String, nullable=True)
    previous_content_hash = Column(String, nullable=True)

    filesystem_write_performed = Column(Boolean, default=False, nullable=False)
    disk_write_performed = Column(Boolean, default=False, nullable=False)
    runtime_server_started = Column(Boolean, default=False, nullable=False)
    preview_server_started = Column(Boolean, default=False, nullable=False)
    generated_code_execution_performed = Column(Boolean, default=False, nullable=False)
    repair_applied = Column(Boolean, default=False, nullable=False)

    metadata_json = Column(Text, default="{}", nullable=False)
    requested_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformSelfBuildModuleRequest(PlatformBase):
    __tablename__ = "platform_self_build_module_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="request_recorded", index=True, nullable=False)
    requested_by = Column(String, default="platform_admin", nullable=False)
    module_name = Column(String, nullable=False)
    module_goal = Column(Text, nullable=False)
    acceptance_criteria_json = Column(Text, default="[]", nullable=False)
    notes = Column(Text, default="", nullable=False)
    workflow_run_id = Column(String, index=True, nullable=True)
    handoff_status = Column(String, default="waiting_for_app_build_workflow", index=True, nullable=False)
    linked_by = Column(String, nullable=True)
    safety_mode = Column(String, default="self_build_module_request_v78_request_tracking_only", index=True, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformSelfBuildModuleRequestEvent(PlatformBase):
    __tablename__ = "platform_self_build_module_request_events"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    module_name = Column(String, nullable=True)
    details_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformModuleRolloutDecision(PlatformBase):
    __tablename__ = "platform_module_rollout_decisions"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    approval_status = Column(String, index=True, nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    rejected = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String, nullable=True)
    rejected_by = Column(String, nullable=True)
    reason = Column(Text, default="", nullable=False)
    rollout_execution_allowed = Column(Boolean, default=False, nullable=False)
    rollout_execution_performed = Column(Boolean, default=False, nullable=False)
    safety_mode = Column(String, default="module_rollout_gate_v79_gate_only", index=True, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)
    decided_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformModuleRolloutEvent(PlatformBase):
    __tablename__ = "platform_module_rollout_events"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=True)
    details_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
