from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.platform.api.security import require_platform_admin
from app.platform.services.internal_dogfooding_module_service import (
    create_internal_dogfooding_module_request,
    decide_internal_dogfooding_rollout,
    get_internal_dogfooding_module_history,
    inspect_internal_dogfooding_module,
    link_internal_dogfooding_module_to_workflow,
)
from app.platform.services.module_rollout_gate_service import (
    approve_module_rollout,
    get_module_rollout_history,
    inspect_module_rollout_gate,
    reject_module_rollout,
)
from app.platform.services.self_build_module_request_service import (
    create_self_build_module_request,
    get_self_build_module_request,
    inspect_self_build_module_request_handoff,
    link_self_build_module_request_to_workflow,
    list_self_build_module_requests,
)


router = APIRouter()


@router.post("/internal-dogfooding/module")
def post_app_build_internal_dogfooding_module(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return create_internal_dogfooding_module_request(
        requested_by=str(payload.get("requested_by") or "platform_admin"),
        workflow_run_id=payload.get("workflow_run_id"),
        module_name=payload.get("module_name"),
        module_goal=payload.get("module_goal"),
        acceptance_criteria=payload.get("acceptance_criteria"),
        notes=payload.get("notes"),
    )


@router.post("/internal-dogfooding/module/{request_id}/link-workflow")
def post_app_build_internal_dogfooding_module_link_workflow(
    request_id: str,
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return link_internal_dogfooding_module_to_workflow(
        request_id=request_id,
        workflow_run_id=str(payload.get("workflow_run_id") or ""),
        linked_by=str(payload.get("linked_by") or "platform_admin"),
    )


@router.get("/internal-dogfooding/module/{request_id}/inspect")
def get_app_build_internal_dogfooding_module_inspect(
    request_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return inspect_internal_dogfooding_module(request_id=request_id)


@router.post("/internal-dogfooding/module/{request_id}/decision")
def post_app_build_internal_dogfooding_module_decision(
    request_id: str,
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return decide_internal_dogfooding_rollout(
        request_id=request_id,
        decision=str(payload.get("decision") or ""),
        decided_by=str(payload.get("decided_by") or "platform_admin"),
        reason=payload.get("reason"),
    )


@router.get("/internal-dogfooding/module/{request_id}/history")
def get_app_build_internal_dogfooding_module_history(
    request_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_internal_dogfooding_module_history(request_id)


@router.get("/module-rollout/{request_id}/status")
def get_app_build_module_rollout_status(
    request_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return inspect_module_rollout_gate(request_id)


@router.post("/module-rollout/{request_id}/approve")
def post_app_build_module_rollout_approve(
    request_id: str,
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return approve_module_rollout(
        request_id=request_id,
        approved_by=str(payload.get("approved_by") or "platform_admin"),
        reason=payload.get("reason"),
    )


@router.post("/module-rollout/{request_id}/reject")
def post_app_build_module_rollout_reject(
    request_id: str,
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return reject_module_rollout(
        request_id=request_id,
        rejected_by=str(payload.get("rejected_by") or "platform_admin"),
        reason=payload.get("reason"),
    )


@router.get("/module-rollout/{request_id}/history")
def get_app_build_module_rollout_history(
    request_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_module_rollout_history(request_id)


@router.post("/module-requests")
def post_app_build_module_request(
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return create_self_build_module_request(
        module_name=payload.get("module_name"),
        module_goal=payload.get("module_goal"),
        requested_by=str(payload.get("requested_by") or "platform_admin"),
        workflow_run_id=payload.get("workflow_run_id"),
        acceptance_criteria=payload.get("acceptance_criteria") or [],
        notes=payload.get("notes"),
    )


@router.get("/module-requests")
def get_app_build_module_requests(
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return list_self_build_module_requests()


@router.get("/module-requests/{request_id}")
def get_app_build_module_request(
    request_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return get_self_build_module_request(request_id)


@router.post("/module-requests/{request_id}/link-workflow")
def post_app_build_module_request_link_workflow(
    request_id: str,
    payload: Dict[str, Any],
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return link_self_build_module_request_to_workflow(
        request_id=request_id,
        workflow_run_id=str(payload.get("workflow_run_id") or ""),
        linked_by=str(payload.get("linked_by") or "platform_admin"),
    )


@router.get("/module-requests/{request_id}/handoff")
def get_app_build_module_request_handoff(
    request_id: str,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return inspect_self_build_module_request_handoff(request_id)

