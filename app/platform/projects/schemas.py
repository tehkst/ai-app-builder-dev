from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    CREATED = "created"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class RuntimeStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    REPAIRING = "repairing"


class DeploymentStatus(str, Enum):
    NOT_DEPLOYED = "not_deployed"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class ProjectRecord(BaseModel):
    project_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)

    generation_status: GenerationStatus = GenerationStatus.CREATED
    runtime_status: RuntimeStatus = RuntimeStatus.NOT_RUN
    deployment_status: DeploymentStatus = DeploymentStatus.NOT_DEPLOYED

    current_version: int = 1

    generation_count: int = 0
    repair_count: int = 0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(BaseModel):
    project_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
