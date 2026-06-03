import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.platform.projects.schemas import ProjectRecord
from app.platform.tenants.schemas import TenantRecord
from app.platform.workspaces.schemas import WorkspaceRegistryRecord


def utc_now():
    return datetime.now(timezone.utc)


def encode_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    return json.dumps(metadata or {})


def decode_metadata(metadata_json: Optional[str]) -> Dict[str, Any]:
    if not metadata_json:
        return {}

    try:
        decoded = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}

    if not isinstance(decoded, dict):
        return {}

    return decoded


def tenant_model_to_record(model) -> TenantRecord:
    return TenantRecord(
        tenant_id=model.tenant_id,
        name=model.name,
        owner_id=model.owner_id,
        status=model.status,
        plan=model.plan,
        created_at=model.created_at,
        updated_at=model.updated_at,
        metadata=decode_metadata(model.metadata_json),
    )


def workspace_model_to_record(model) -> WorkspaceRegistryRecord:
    return WorkspaceRegistryRecord(
        tenant_id=model.tenant_id,
        workspace_id=model.workspace_id,
        project_id="",
        owner_id=model.owner_id,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
        metadata=decode_metadata(model.metadata_json),
    )


def project_model_to_record(model) -> ProjectRecord:
    return ProjectRecord(
        project_id=model.project_id,
        tenant_id=model.tenant_id,
        workspace_id=model.workspace_id,
        generation_status=model.generation_status,
        runtime_status=model.runtime_status,
        deployment_status=model.deployment_status,
        current_version=model.current_version,
        generation_count=model.generation_count,
        repair_count=model.repair_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
        metadata=decode_metadata(model.metadata_json),
    )
