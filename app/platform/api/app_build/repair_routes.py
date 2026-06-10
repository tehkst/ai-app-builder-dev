from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.repair_approval_gate_service import (
    approve_repair_plan,
    assert_repair_apply_allowed,
    get_repair_approval_status,
    reject_repair_plan,
)
from app.platform.services.repair_executor_service import (
    build_replace_file_operation,
    execute_approved_repair,
    get_repair_execution_history,
)
from app.platform.services.repair_plan_generator_service import generate_repair_plan_for_workflow
from app.platform.services.repair_rerun_coordinator_service import (
    get_repair_rerun_history,
    rerun_after_successful_repair,
)
from app.platform.services.self_healing_loop_coordinator_service import (
    get_self_healing_loop_history,
    inspect_self_healing_loop,
    run_self_healing_loop_once,
)


router = APIRouter()


@router.get("/runs/{workflow_run_id}/self-healing-loop/status")
def get_app_build_self_healing_loop_status(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return inspect_self_healing_loop(
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/self-healing-loop/history")
def get_app_build_self_healing_loop_history(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_self_healing_loop_history(
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/self-healing-loop/run-once")
def post_app_build_self_healing_loop_run_once(
    workflow_run_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_platform_db),
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return run_self_healing_loop_once(
        db=db,
        workflow_run_id=workflow_run_id,
        requested_by=str(payload.get("requested_by") or "platform_admin"),
    )


@router.get("/runs/{workflow_run_id}/repair-rerun/history")
def get_app_build_repair_rerun_history(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_repair_rerun_history(
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/repair-rerun/start")
def post_app_build_repair_rerun_start(
    workflow_run_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_platform_db),
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return rerun_after_successful_repair(
        db=db,
        workflow_run_id=workflow_run_id,
        requested_by="platform_admin",
        perform_install=bool(payload.get("perform_install") or False),
    )


@router.get("/runs/{workflow_run_id}/repair-execution/history")
def get_app_build_repair_execution_history(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_repair_execution_history(
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/repair-execution/replace-file")
def post_app_build_repair_execution_replace_file(
    workflow_run_id: str,
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    operation = build_replace_file_operation(
        target_relative_path=str(payload.get("target_relative_path") or ""),
        replacement_content=str(payload.get("replacement_content") or ""),
        reason=str(payload.get("reason") or "Dashboard requested approved repair replacement."),
    )
    return execute_approved_repair(
        workflow_run_id=workflow_run_id,
        sandbox_root=str(payload.get("sandbox_root") or ""),
        operations=[operation],
        requested_by="platform_admin",
    )


@router.get("/runs/{workflow_run_id}/repair-approval/status")
def get_app_build_repair_approval_status(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_repair_approval_status(
        workflow_run_id=workflow_run_id,
    )


@router.post("/runs/{workflow_run_id}/repair-approval/approve")
def post_app_build_repair_approval_approve(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return approve_repair_plan(
        workflow_run_id=workflow_run_id,
        approved_by="platform_admin",
    )


@router.post("/runs/{workflow_run_id}/repair-approval/reject")
def post_app_build_repair_approval_reject(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return reject_repair_plan(
        workflow_run_id=workflow_run_id,
        rejected_by="platform_admin",
    )


@router.get("/runs/{workflow_run_id}/repair-approval/apply-gate")
def get_app_build_repair_approval_apply_gate(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return assert_repair_apply_allowed(
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/repair-plan")
def get_app_build_repair_plan(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return generate_repair_plan_for_workflow(
        workflow_run_id=workflow_run_id,
    )

