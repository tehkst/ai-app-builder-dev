from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


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

class PlatformGeneratedFileVersion(PlatformBase):
    __tablename__ = "platform_generated_file_versions"

    id = Column(Integer, primary_key=True, index=True)
    generated_file_version_id = Column(String, unique=True, index=True, nullable=False)

    generated_file_id = Column(String, index=True, nullable=False)
    workflow_run_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    project_id = Column(String, index=True, nullable=True)

    version_number = Column(Integer, default=1, index=True, nullable=False)
    previous_content_hash = Column(String, index=True, nullable=True)
    content_hash = Column(String, index=True, nullable=False)

    content_preview = Column(Text, default="", nullable=False)
    path = Column(String, index=True, nullable=False)
    language = Column(String, nullable=True)
    purpose = Column(Text, nullable=True)

    source_step_id = Column(String, index=True, nullable=True)
    source_agent_id = Column(String, index=True, nullable=True)

    snapshot_status = Column(String, default="created", index=True, nullable=False)
    restore_status = Column(String, default="not_restored", index=True, nullable=False)

    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
