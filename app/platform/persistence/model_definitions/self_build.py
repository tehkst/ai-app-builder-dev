from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


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
