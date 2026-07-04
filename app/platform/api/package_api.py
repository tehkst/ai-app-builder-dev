from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.persistence.database import get_platform_db
from app.platform.services.senior_software_engineer import create_implementation_package, format_implementation_package_markdown

router = APIRouter(prefix="/platform/senior-engineer", tags=["platform"])


class PackageRequest(BaseModel):
    token: Optional[str] = None
    goal: str
    scope: str = "mission_control"


@router.post("/implementation-package")
def build_package(payload: PackageRequest, db: Session = Depends(get_platform_db)) -> Dict[str, Any]:
    package = create_implementation_package(goal=payload.goal, db=db, scope=payload.scope)
    return {"implementation_package": package, "markdown": format_implementation_package_markdown(package)}
