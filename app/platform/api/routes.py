import json
import subprocess
import sys
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter
from app.platform.persistence.models import (
    PlatformGenerationRun,
    PlatformProject,
    PlatformTenant,
    PlatformWorkspace,
)


router = APIRouter(prefix="/platform", tags=["platform"])


MAX_LIST_LIMIT = 100
COMMAND_TIMEOUT_SECONDS = 300


def extract_json_block(stdout: str) -> Optional[dict]:
    start = stdout.find("{")
    end = stdout.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None


def run_platform_command(command: list, timeout: int = COMMAND_TIMEOUT_SECONDS) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        parsed_output = extract_json_block(result.stdout)

        return {
            "passed": result.returncode == 0,
            "return_code": result.returncode,
            "command": " ".join(command),
            "parsed_output": parsed_output,
            "stdout": result.stdout,
            "stderr": result.stderr if result.returncode != 0 else "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "passed": False,
            "return_code": None,
            "command": " ".join(command),
            "parsed_output": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "timed_out": True,
            "timeout_seconds": timeout,
        }


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1

    if limit > MAX_LIST_LIMIT:
        return MAX_LIST_LIMIT

    return limit


@router.get("/tenants")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_tenants(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    tenants = db.query(PlatformTenant).order_by(PlatformTenant.id.desc()).limit(safe_limit).all()

    return {
        "items": [
            {
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "status": tenant.status,
                "plan": tenant.plan,
                "owner_id": tenant.owner_id,
            }
            for tenant in tenants
        ],
        "limit": safe_limit,
    }


@router.get("/workspaces")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_workspaces(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    workspaces = (
        db.query(PlatformWorkspace)
        .order_by(PlatformWorkspace.id.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "items": [
            {
                "tenant_id": workspace.tenant_id,
                "workspace_id": workspace.workspace_id,
                "status": workspace.status,
                "owner_id": workspace.owner_id,
            }
            for workspace in workspaces
        ],
        "limit": safe_limit,
    }


@router.get("/projects")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_projects(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    projects = db.query(PlatformProject).order_by(PlatformProject.id.desc()).limit(safe_limit).all()

    return {
        "items": [
            {
                "tenant_id": project.tenant_id,
                "workspace_id": project.workspace_id,
                "project_id": project.project_id,
                "generation_status": project.generation_status,
                "runtime_status": project.runtime_status,
                "deployment_status": project.deployment_status,
                "current_version": project.current_version,
                "generation_count": project.generation_count,
                "repair_count": project.repair_count,
            }
            for project in projects
        ],
        "limit": safe_limit,
    }


@router.get("/generation-runs")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_generation_runs(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    generation_runs = (
        db.query(PlatformGenerationRun)
        .order_by(PlatformGenerationRun.id.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "items": [
            {
                "run_id": generation_run.run_id,
                "tenant_id": generation_run.tenant_id,
                "workspace_id": generation_run.workspace_id,
                "project_id": generation_run.project_id,
                "status": generation_run.status,
                "review_status": generation_run.review_status,
                "runtime_status": generation_run.runtime_status,
                "error_summary": generation_run.error_summary,
                "started_at": generation_run.started_at,
                "completed_at": generation_run.completed_at,
            }
            for generation_run in generation_runs
        ],
        "limit": safe_limit,
    }


@router.get("/repair/health")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def get_repair_health(
    request: Request,
    platform_admin=Depends(require_platform_admin),
):
    return run_platform_command(
        [
            sys.executable,
            "-m",
            "app.platform.repair.health",
        ]
    )


@router.post("/repair/workflow")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def run_repair_workflow(
    request: Request,
    summary: bool = True,
    platform_admin=Depends(require_platform_admin),
):
    command = [
        sys.executable,
        "-m",
        "app.platform.repair.workflow",
        "--dry-run",
    ]

    if summary:
        command.append("--summary")

    return run_platform_command(command)


@router.get("/repair/reports")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_repair_reports(
    request: Request,
    limit: int = 10,
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)

    return run_platform_command(
        [
            sys.executable,
            "-m",
            "app.platform.repair.list_reports",
            "--limit",
            str(safe_limit),
        ]
    )


@router.get("/release-gate/fast")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def run_fast_release_gate(
    request: Request,
    platform_admin=Depends(require_platform_admin),
):
    return run_platform_command(
        [
            sys.executable,
            "-m",
            "app.platform.release_gate",
            "--mode",
            "fast",
        ]
    )
