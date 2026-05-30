from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


async def create_project_record(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    organization_id: str,
    raw_prompt: str,
    state: dict,
):
    project = Project(
        project_id=project_id,
        user_id=user_id,
        organization_id=organization_id,
        raw_prompt=raw_prompt,
        current_step=state.get("current_step", "created"),
        approval_type=state.get("approval_type"),
        state=state,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    return project


async def get_project_by_project_id(
    db: AsyncSession,
    project_id: str,
):
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )

    return result.scalar_one_or_none()


async def update_project_state(
    db: AsyncSession,
    project: Project,
    state: dict,
):
    project.current_step = state.get("current_step", project.current_step)
    project.approval_type = state.get("approval_type")
    project.state = state

    await db.commit()
    await db.refresh(project)

    return project
