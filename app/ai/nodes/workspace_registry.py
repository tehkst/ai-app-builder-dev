from typing import Tuple

from app.ai.state import ProjectState
from app.platform.persistence.crud import (
    complete_generation_run,
    create_generation_run,
    fail_generation_run,
)
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.workspaces.db_registry import db_workspace_registry as workspace_registry
from app.platform.workspaces.schemas import (
    WorkspaceRegistryCreate,
    WorkspaceStatus,
)


DEFAULT_TENANT_ID = "default-tenant"
DEFAULT_WORKSPACE_ID = "default-workspace"


def get_workspace_ids(state: ProjectState) -> Tuple[str, str, str]:
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

    db = PlatformSessionLocal()

    try:
        generation_run = create_generation_run(
            db,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            metadata={
                "raw_prompt": state.get("raw_prompt"),
            },
        )
    finally:
        db.close()

    return {
        **state,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "generation_run_id": generation_run.run_id,
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

    generation_run_id = state.get("generation_run_id")

    if generation_run_id:
        db = PlatformSessionLocal()

        try:
            complete_generation_run(
                db,
                run_id=generation_run_id,
                review_status=state.get("review_status"),
                runtime_status="passed",
                metadata={
                    "current_step": state.get("current_step"),
                    "runtime_report": state.get("runtime_report"),
                },
            )
        finally:
            db.close()

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

    generation_run_id = state.get("generation_run_id")

    if generation_run_id:
        db = PlatformSessionLocal()

        try:
            fail_generation_run(
                db,
                run_id=generation_run_id,
                error_summary=state.get("errors") or "Generation failed",
                review_status=state.get("review_status"),
                runtime_status="failed" if state.get("runtime_report") else None,
                metadata={
                    "current_step": state.get("current_step"),
                    "review_feedback": state.get("review_feedback"),
                    "runtime_report": state.get("runtime_report"),
                },
            )
        finally:
            db.close()

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
