from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformExecutionWorkspace(PlatformBase):
    __tablename__ = "platform_execution_workspaces"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, unique=True, index=True, nullable=False)
    mission_id = Column(String, index=True, nullable=False)
    owner_id = Column(String, index=True, nullable=False)
    repository = Column(String, nullable=False)
    branch = Column(String, nullable=True)
    local_path = Column(Text, nullable=True)
    status = Column(String, index=True, nullable=False, default="created")
    lease_owner = Column(String, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    recovery_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PlatformGovernanceApproval(PlatformBase):
    __tablename__ = "platform_governance_approvals"

    id = Column(Integer, primary_key=True)
    approval_id = Column(String, unique=True, index=True, nullable=False)
    mission_id = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    scope = Column(String, nullable=False)
    target = Column(String, nullable=False)
    approved_by = Column(String, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PlatformExecutionEvidence(PlatformBase):
    __tablename__ = "platform_execution_evidence"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(String, unique=True, index=True, nullable=False)
    mission_id = Column(String, index=True, nullable=False)
    actor = Column(String, index=True, nullable=False)
    capability = Column(String, index=True, nullable=False)
    requested_action = Column(String, nullable=False)
    authorization_json = Column(Text, nullable=False)
    outcome = Column(String, index=True, nullable=False)
    artifact_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PlatformWorkspaceArtifact(PlatformBase):
    __tablename__ = "platform_workspace_artifacts"

    id = Column(Integer, primary_key=True)
    artifact_id = Column(String, unique=True, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    artifact_type = Column(String, index=True, nullable=False)
    path = Column(Text, nullable=True)
    sha256 = Column(String, nullable=True)
    content_base64 = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
