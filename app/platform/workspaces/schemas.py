from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkspaceStatus(str, Enum):
    CREATED = "created"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class DeploymentStatus(str, Enum):
    NOT_DEPLOYED = "not_deployed"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class WorkspaceRegistryRecord(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    owner_id: str | None = None
    status: WorkspaceStatus = WorkspaceStatus.CREATED
    deployment_status: DeploymentStatus = DeploymentStatus.NOT_DEPLOYED
    generation_count: int = 0
    repair_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceRegistryCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    owner_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
