from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_current_user
from app.models.user import User
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.langgraph_app.graph import build_app_builder_graph
from app.langgraph_app.resume_graph import build_resume_graph
from app.services.file_writer_service import safe_write_generated_files
from app.services.project_service import (
    create_project_record,
    get_project_by_project_id,
    update_project_state,
)

router = APIRouter()


class StartProjectRequest(BaseModel):
    project_id: str
    user_id: str
    organization_id: str
    raw_prompt: str


class ApprovalRequest(BaseModel):
    approved: bool


@router.post("/start")
async def start_project(
    request: StartProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    graph = build_app_builder_graph()

    initial_state = {
        "project_id": request.project_id,
        "user_id": current.user_id,
        "organization_id": request.organization_id,
        "raw_prompt": request.raw_prompt,
    }

    result = await graph.ainvoke(initial_state)

    await create_project_record(
        db=db,
        project_id=request.project_id,
        user_id=current.user_id,
        organization_id=request.organization_id,
        raw_prompt=request.raw_prompt,
        state=result,
    )

    return {
        "project_id": request.project_id,
        "current_step": result.get("current_step"),
        "approval_type": result.get("approval_type"),
        "product_spec": result.get("product_spec"),
    }


@router.post("/{project_id}/approve")
async def approve_project(
    project_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await get_project_by_project_id(db, project_id)

    if not project:
        return {"error": "Project not found"}

    existing_state = project.state
    existing_state["approved"] = request.approved

    if not request.approved:
        existing_state["current_step"] = "rejected_by_human"
        await update_project_state(db, project, existing_state)
        return existing_state

    resume_graph = build_resume_graph()
    result = await resume_graph.ainvoke(existing_state)

    await update_project_state(db, project, result)

    return {
        "project_id": project_id,
        "current_step": result.get("current_step"),
        "approval_type": result.get("approval_type"),
        "architecture_plan": result.get("architecture_plan"),
        "qa_report": result.get("qa_report"),
        "security_report": result.get("security_report"),
        "generated_files": result.get("generated_files"),
    }


@router.post("/{project_id}/finalize")
async def finalize_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await get_project_by_project_id(db, project_id)

    if not project:
        return {"error": "Project not found"}

    existing_state = project.state

    if existing_state.get("approval_type") != "generated_app":
        return {
            "error": "Project is not ready for final generated app approval"
        }

    if existing_state.get("security_report", {}).get("risk_level") != "low":
        return {
            "error": "Project failed security review and cannot be finalized"
        }

    written_files = safe_write_generated_files(
        project_id=project_id,
        generated_files=existing_state.get("generated_files", []),
    )

    existing_state["approved"] = True
    existing_state["current_step"] = "generated_app_finalized"
    existing_state["written_files"] = written_files

    await update_project_state(db, project, existing_state)

    return {
        "project_id": project_id,
        "current_step": existing_state["current_step"],
        "written_files": written_files,
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await get_project_by_project_id(db, project_id)

    if not project:
        return {"error": "Project not found"}

    return {
        "project_id": project.project_id,
        "user_id": project.user_id,
        "organization_id": project.organization_id,
        "current_step": project.current_step,
        "approval_type": project.approval_type,
        "state": project.state,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }
