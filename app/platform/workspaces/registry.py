from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.platform.workspaces.schemas import (
    DeploymentStatus,
    WorkspaceRegistryCreate,
    WorkspaceRegistryRecord,
    WorkspaceStatus,
)


class WorkspaceRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, WorkspaceRegistryRecord] = {}

    def _key(self, tenant_id: str, workspace_id: str, project_id: str) -> str:
        return f"{tenant_id}:{workspace_id}:{project_id}"

    def create_workspace(self, payload: WorkspaceRegistryCreate) -> WorkspaceRegistryRecord:
        key = self._key(payload.tenant_id, payload.workspace_id, payload.project_id)

        if key in self._records:
            return self._records[key]

        record = WorkspaceRegistryRecord(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            owner_id=payload.owner_id,
            metadata=payload.metadata,
        )
        self._records[key] = record
        return record

    def get_workspace(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> Optional[WorkspaceRegistryRecord]:
        return self._records.get(self._key(tenant_id, workspace_id, project_id))

    def list_workspaces_for_tenant(self, tenant_id: str) -> List[WorkspaceRegistryRecord]:
        return [
            record
            for record in self._records.values()
            if record.tenant_id == tenant_id
        ]

    def update_workspace_status(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        status: WorkspaceStatus,
    ) -> WorkspaceRegistryRecord:
        record = self._require_workspace(tenant_id, workspace_id, project_id)
        updated = record.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._records[self._key(tenant_id, workspace_id, project_id)] = updated
        return updated

    def update_deployment_status(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        deployment_status: DeploymentStatus,
    ) -> WorkspaceRegistryRecord:
        record = self._require_workspace(tenant_id, workspace_id, project_id)
        updated = record.model_copy(
            update={
                "deployment_status": deployment_status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._records[self._key(tenant_id, workspace_id, project_id)] = updated
        return updated

    def increment_generation_count(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> WorkspaceRegistryRecord:
        record = self._require_workspace(tenant_id, workspace_id, project_id)
        updated = record.model_copy(
            update={
                "generation_count": record.generation_count + 1,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._records[self._key(tenant_id, workspace_id, project_id)] = updated
        return updated

    def increment_repair_count(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> WorkspaceRegistryRecord:
        record = self._require_workspace(tenant_id, workspace_id, project_id)
        updated = record.model_copy(
            update={
                "repair_count": record.repair_count + 1,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._records[self._key(tenant_id, workspace_id, project_id)] = updated
        return updated

    def _require_workspace(
        self,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> WorkspaceRegistryRecord:
        record = self.get_workspace(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
        )

        if record is None:
            raise KeyError("Workspace registry record was not found")

        return record


workspace_registry = WorkspaceRegistry()
