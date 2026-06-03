from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
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
