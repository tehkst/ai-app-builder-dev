from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.controlled_sandbox_runtime_service import (
    get_controlled_sandbox_runtime_logs,
    get_controlled_sandbox_runtime_status,
    start_controlled_sandbox_runtime_for_workflow,
    stop_controlled_sandbox_runtime,
)
from app.platform.services.runtime_approval_gate_service import (
    approve_runtime_run_plan_for_workflow,
    get_latest_runtime_approval_for_workflow,
    reject_runtime_run_plan_for_workflow,
)
from app.platform.services.runtime_failure_analyzer_service import analyze_runtime_failure_for_workflow
from app.platform.services.runtime_readiness_detector_service import detect_runtime_readiness_for_workflow
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_workflow


router = APIRouter()


@router.get("/runs/{workflow_run_id}/runtime-readiness")
def inspect_app_build_run_runtime_readiness(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return detect_runtime_readiness_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/runtime-run-plan")
def build_app_build_run_runtime_run_plan(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return build_runtime_run_plan_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/runtime-approval/approve")
def approve_app_build_run_runtime_approval(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return approve_runtime_run_plan_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/runtime-approval/reject")
def reject_app_build_run_runtime_approval(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return reject_runtime_run_plan_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/runtime-approval/latest")
def get_app_build_run_latest_runtime_approval(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_latest_runtime_approval_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/controlled-sandbox-runtime/start")
def start_app_build_controlled_sandbox_runtime(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return start_controlled_sandbox_runtime_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
        perform_install=False,
    )


@router.get("/runs/{workflow_run_id}/controlled-sandbox-runtime/status")
def get_app_build_controlled_sandbox_runtime_status(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_controlled_sandbox_runtime_status(
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/runtime-failure-analysis")
def get_app_build_runtime_failure_analysis(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return analyze_runtime_failure_for_workflow(
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/controlled-sandbox-runtime/logs")
def get_app_build_controlled_sandbox_runtime_logs(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_controlled_sandbox_runtime_logs(
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/controlled-sandbox-runtime/stop")
def stop_app_build_controlled_sandbox_runtime(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return stop_controlled_sandbox_runtime(
        workflow_run_id=workflow_run_id,
    )

