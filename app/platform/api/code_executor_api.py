from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.code_executor import create_code_execution_plan, format_code_execution_plan_markdown

router = APIRouter(prefix="/platform/code-executor", tags=["platform"])


class CodeExecutionPlanRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    scope: str = "mission_control"


@router.post("/plan")
def plan(payload: CodeExecutionPlanRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    execution_plan = create_code_execution_plan(goal=payload.goal, db=db, scope=payload.scope)
    return {
        "execution_plan": execution_plan,
        "markdown": format_code_execution_plan_markdown(execution_plan),
    }
