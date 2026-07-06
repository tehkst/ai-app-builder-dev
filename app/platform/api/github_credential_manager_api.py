from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from app.platform.services.github_credential_manager import (
    github_connection_test,
    github_credential_status,
    validate_repository_access_request,
    format_github_credential_markdown,
)

router = APIRouter(prefix="/platform/github-credentials", tags=["platform"])


class RepositoryAccessValidationRequest(BaseModel):
    repository: str = "tehkst/ai-app-builder-dev"
    action: str
    approved: bool = False


@router.get("/status")
def status() -> Dict[str, Any]:
    payload = github_credential_status()
    return {
        "github_credential_manager": payload,
        "markdown": format_github_credential_markdown(payload),
    }


@router.get("/connection-test")
def connection_test() -> Dict[str, Any]:
    return github_connection_test()


@router.post("/validate-access")
def validate_access(payload: RepositoryAccessValidationRequest) -> Dict[str, Any]:
    return validate_repository_access_request(
        repository=payload.repository,
        action=payload.action,
        approved=payload.approved,
    )
