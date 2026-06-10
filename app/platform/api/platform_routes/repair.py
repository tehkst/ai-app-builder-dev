import sys

from fastapi import APIRouter, Depends, Request

from app.platform.api.security import require_platform_admin
from app.platform.api.platform_routes.shared import clamp_limit, run_platform_command
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter


router = APIRouter()


@router.get("/repair/health")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def get_repair_health(request: Request, platform_admin=Depends(require_platform_admin)):
    return run_platform_command([sys.executable, "-m", "app.platform.repair.health"])


@router.post("/repair/workflow")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def run_repair_workflow(
    request: Request,
    summary: bool = True,
    platform_admin=Depends(require_platform_admin),
):
    command = [sys.executable, "-m", "app.platform.repair.workflow", "--dry-run"]
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
        [sys.executable, "-m", "app.platform.repair.list_reports", "--limit", str(safe_limit)]
    )


@router.get("/release-gate/fast")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def run_fast_release_gate(request: Request, platform_admin=Depends(require_platform_admin)):
    return run_platform_command([sys.executable, "-m", "app.platform.release_gate", "--mode", "fast"])
