from typing import List, Optional

from app.platform.persistence.crud import (
    create_project,
    create_tenant,
    create_workspace,
    get_project,
    increment_project_generation_count,
    increment_project_repair_count,
    update_project_generation_status,
)
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.repository import project_model_to_record
from app.platform.workspaces.schemas import (
    DeploymentStatus,
    WorkspaceRegistryCreate,
    WorkspaceRegistryRecord,
    WorkspaceStatus,
)


class DatabaseWorkspaceRegistry:
    def __init__(self) -> None:
        create_platform_tables()

    def create_workspace(self, payload: WorkspaceRegistryCreate) -> WorkspaceRegistryRecord:
        db = PlatformSessionLocal()

        try:
            create_tenant(
                db,
                tenant_id=payload.tenant_id,
                name=payload.tenant_id,
                owner_id=payload.owner_id,
            )
            create_workspace(
                db,
                tenant_id=payload.tenant_id,
                workspace_id=payload.workspace_id,
                owner_id=payload.owner_id,
                metadata=payload.metadata,
            )
            project = create_project(
                db,
                tenant_id=payload.tenant_id,
                workspace_id=payload.workspace_id,
                project_id=payload.project_id,
                metadata=payload.metadata,
            )

            return self._project_to_workspace_record(project)

        finally:
            db.close()

    def get_workspace(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> Optional[WorkspaceRegistryRecord]:
        db = PlatformSessionLocal()

        try:
            project = get_project(
                db,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                project_id=project_id,
            )

            if project is None:
                return None

            return self._project_to_workspace_record(project)

        finally:
            db.close()

    def list_workspaces_for_tenant(self, tenant_id: str) -> List[WorkspaceRegistryRecord]:
        return []

    def update_workspace_status(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        status: WorkspaceStatus,
    ) -> WorkspaceRegistryRecord:
        db = PlatformSessionLocal()

        try:
            project = update_project_generation_status(
                db,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                project_id=project_id,
                generation_status=status.value,
            )
            return self._project_to_workspace_record(project)

        finally:
            db.close()

    def update_deployment_status(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        deployment_status: DeploymentStatus,
    ) -> WorkspaceRegistryRecord:
        record = self.get_workspace(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
        )

        if record is None:
            raise KeyError("Workspace registry record was not found")

        return record

    def increment_generation_count(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> WorkspaceRegistryRecord:
        db = PlatformSessionLocal()

        try:
            project = increment_project_generation_count(
                db,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                project_id=project_id,
            )
            return self._project_to_workspace_record(project)

        finally:
            db.close()

    def increment_repair_count(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
    ) -> WorkspaceRegistryRecord:
        db = PlatformSessionLocal()

        try:
            project = increment_project_repair_count(
                db,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                project_id=project_id,
            )
            return self._project_to_workspace_record(project)

        finally:
            db.close()

    def _project_to_workspace_record(self, project) -> WorkspaceRegistryRecord:
        project_record = project_model_to_record(project)

        return WorkspaceRegistryRecord(
            tenant_id=project_record.tenant_id,
            workspace_id=project_record.workspace_id,
            project_id=project_record.project_id,
            owner_id=None,
            status=WorkspaceStatus(project_record.generation_status),
            deployment_status=DeploymentStatus(project_record.deployment_status),
            generation_count=project_record.generation_count,
            repair_count=project_record.repair_count,
            created_at=project_record.created_at,
            updated_at=project_record.updated_at,
            metadata=project_record.metadata,
        )


db_workspace_registry = DatabaseWorkspaceRegistry()
