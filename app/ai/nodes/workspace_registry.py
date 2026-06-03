from app.ai.state import ProjectState
from app.platform.workspaces.registry import workspace_registry
from app.platform.workspaces.schemas import (
    WorkspaceRegistryCreate,
    WorkspaceStatus,
)


DEFAULT_TENANT_ID = "default-tenant"
DEFAULT_WORKSPACE_ID = "default-workspace"


def get_workspace_ids(state: ProjectState) -> tuple[str, str, str]:
    tenant_id = state.get("tenant_id", DEFAULT_TENANT_ID)
    workspace_id = state.get("workspace_id", DEFAULT_WORKSPACE_ID)
    project_id = state["project_id"]
    return tenant_id, workspace_id, project_id


def workspace_generation_started_node(state: ProjectState) -> ProjectState:
    tenant_id, workspace_id, project_id = get_workspace_ids(state)

    record = workspace_registry.create_workspace(
        WorkspaceRegistryCreate(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            owner_id=state.get("owner_id"),
            metadata={
                "raw_prompt": state.get("raw_prompt"),
            },
        )
    )
    record = workspace_registry.increment_generation_count(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )
    record = workspace_registry.update_workspace_status(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        status=WorkspaceStatus.GENERATING,
    )

    return {
        **state,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "workspace_registry_record": record.model_dump(),
        "current_step": "workspace_generation_started",
    }


def workspace_generation_ready_node(state: ProjectState) -> ProjectState:
    tenant_id, workspace_id, project_id = get_workspace_ids(state)

    record = workspace_registry.update_workspace_status(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        status=WorkspaceStatus.READY,
    )

    return {
        **state,
        "workspace_registry_record": record.model_dump(),
        "current_step": "workspace_generation_ready",
    }


def workspace_generation_failed_node(state: ProjectState) -> ProjectState:
    tenant_id, workspace_id, project_id = get_workspace_ids(state)

    record = workspace_registry.update_workspace_status(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        status=WorkspaceStatus.FAILED,
    )

    return {
        **state,
        "workspace_registry_record": record.model_dump(),
        "current_step": "workspace_generation_failed",
    }


def workspace_repair_recorded_node(state: ProjectState) -> ProjectState:
    tenant_id, workspace_id, project_id = get_workspace_ids(state)

    record = workspace_registry.increment_repair_count(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )

    return {
        **state,
        "workspace_registry_record": record.model_dump(),
        "current_step": "workspace_repair_recorded",
    }
