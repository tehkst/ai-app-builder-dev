from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


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
