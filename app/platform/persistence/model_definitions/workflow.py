from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformWorkflowRun(PlatformBase):
    __tablename__ = "platform_workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(String, unique=True, index=True, nullable=False)
    workflow_name = Column(String, default="Agent Workflow", nullable=False)

    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    status = Column(String, default="unknown", index=True, nullable=False)
    plan_status = Column(String, nullable=True)
    simulation = Column(Boolean, default=False, nullable=False)

    step_count = Column(Integer, default=0, nullable=False)
    completed_step_count = Column(Integer, default=0, nullable=False)
    blocked_step_count = Column(Integer, default=0, nullable=False)
    failed_step_count = Column(Integer, default=0, nullable=False)

    missing_capabilities_json = Column(Text, default="[]", nullable=False)
    dependency_repair_plan_json = Column(Text, default="[]", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

class PlatformWorkflowStepRun(PlatformBase):
    __tablename__ = "platform_workflow_step_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(String, index=True, nullable=False)
    step_run_id = Column(String, unique=True, index=True, nullable=False)
    step_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)

    required_capability = Column(String, index=True, nullable=True)
    selected_agent_id = Column(String, index=True, nullable=True)
    status = Column(String, default="unknown", index=True, nullable=False)

    requires_steps_json = Column(Text, default="[]", nullable=False)
    candidate_agents_json = Column(Text, default="[]", nullable=False)
    output_json = Column(Text, default="{}", nullable=False)
    error_json = Column(Text, default="{}", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformAdminWorkflowExecution(PlatformBase):
    __tablename__ = "platform_admin_workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String, unique=True, index=True, nullable=False)
    state = Column(String, default="IDLE", index=True, nullable=False)
    requirements_text = Column(Text, default="", nullable=False)
    scope_markdown = Column(Text, default="", nullable=False)
    generated_code = Column(Text, default="", nullable=False)
    manual_deploy_instructions = Column(Text, default="", nullable=False)
    state_history_json = Column(Text, default="[]", nullable=False)
    cache_snapshot_json = Column(Text, default="{}", nullable=False)
    memory_buffer_json = Column(Text, default="{}", nullable=False)
    alert_message = Column(Text, default="", nullable=False)
    timeout_seconds = Column(Integer, default=900, nullable=False)
    github_push_performed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
