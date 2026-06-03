from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class TenantPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantRecord(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    owner_id: str | None = None
    status: TenantStatus = TenantStatus.ACTIVE
    plan: TenantPlan = TenantPlan.FREE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    owner_id: str | None = None
    plan: TenantPlan = TenantPlan.FREE
    metadata: dict[str, Any] = Field(default_factory=dict)
