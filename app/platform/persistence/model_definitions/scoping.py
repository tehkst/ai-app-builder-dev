from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformScopingRequest(PlatformBase):
    __tablename__ = "platform_scoping_requests"

    id = Column(Integer, primary_key=True, index=True)
    scoping_request_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="clarification_required", index=True, nullable=False)
    approval_status = Column(String, default="not_approved", index=True, nullable=False)
    requested_by = Column(String, default="platform_admin", nullable=False)

    mode_selector = Column(String, index=True, nullable=True)
    target_boundary = Column(String, index=True, nullable=True)
    change_classification = Column(String, index=True, nullable=True)
    request_kind = Column(String, default="platform_self_build", index=True, nullable=False)

    version = Column(Integer, default=1, index=True, nullable=False)
    previous_scoping_request_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)

    normalized_request_json = Column(Text, default="{}", nullable=False)
    questions_json = Column(Text, default="[]", nullable=False)
    scope_of_work_markdown = Column(Text, default="", nullable=False)
    milestone_tree_json = Column(Text, default="[]", nullable=False)
    safety_flags_json = Column(Text, default="{}", nullable=False)
    llm_status = Column(String, default="not_requested", index=True, nullable=False)
    llm_notes_json = Column(Text, default="{}", nullable=False)
    attachments_json = Column(Text, default="[]", nullable=False)

    publish_status = Column(String, default="not_requested", index=True, nullable=False)
    publish_requested_at = Column(DateTime(timezone=True), nullable=True)

    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
