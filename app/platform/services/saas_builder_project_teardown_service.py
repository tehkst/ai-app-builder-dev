from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.deployment.approved_cloud_run import DEFAULT_REGION
from app.platform.persistence.models import (
    PlatformAgentTask,
    PlatformApprovalRequest,
    PlatformAstGraphEdge,
    PlatformAstGraphNode,
    PlatformAuditEvent,
    PlatformGeneratedFile,
    PlatformGeneratedFileRestoreExecution,
    PlatformGeneratedFileVersion,
    PlatformGenerationRun,
    PlatformIngestionEventBuffer,
    PlatformMaterializationApprovalRecord,
    PlatformNeuralDocument,
    PlatformProject,
    PlatformRuntimeApprovalRecord,
    PlatformSemanticEmbedding,
    PlatformWorkflowRun,
    PlatformWorkflowStepRun,
)

# saas_builder projects are NOT PlatformProject/PlatformGenerationRun rows - that is a
# separate, unrelated older generation pipeline never touched by app/platform/saas_builder/.
# A saas_builder project's real identity is its workflow_run_id (PlatformWorkflowRun +
# PlatformWorkflowStepRun rows). These project_id-keyed tables are included only as a
# defensive sweep in case some other subsystem ever wrote a row keyed by the workflow_run_id
# string - harmless no-op for a normal saas_builder project, real safety net otherwise.
_PROJECT_ID_KEYED_MODELS = [
    PlatformGeneratedFile,
    PlatformGeneratedFileVersion,
    PlatformMaterializationApprovalRecord,
    PlatformRuntimeApprovalRecord,
    PlatformGeneratedFileRestoreExecution,
    PlatformAgentTask,
    PlatformApprovalRequest,
    PlatformAuditEvent,
    PlatformNeuralDocument,
    PlatformSemanticEmbedding,
    PlatformAstGraphNode,
    PlatformAstGraphEdge,
    PlatformIngestionEventBuffer,
    PlatformProject,
    PlatformGenerationRun,
]


def find_saas_builder_deployment_identity(db: Session, *, workflow_run_id: str) -> Dict[str, Any]:
    """Locate the real Cloud Run service identity for a saas_builder project by walking the
    mission state JSON stored in its mission_run_state step row - see
    operating_console/mission_run_service.py's _persist for how that blob is written.
    Honest found:False (never fabricated) if no deployment_record artifact and no creation-
    time context.service_name exist.
    """
    from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

    detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    if not detail.get("found"):
        return {"found": False, "reason": "workflow_run_not_found"}

    handler_result: Dict[str, Any] = {}
    for step in detail.get("steps") or []:
        if step.get("step_id") == "mission_run_state" and isinstance(step.get("handler_result"), dict):
            handler_result = step["handler_result"]
            break
    if not handler_result:
        return {"found": False, "reason": "no_mission_run_state"}

    context = handler_result.get("context") if isinstance(handler_result.get("context"), dict) else {}
    if context.get("request_channel") != "saas_builder":
        return {"found": False, "reason": "not_a_saas_builder_project"}

    delivery_contract = handler_result.get("delivery_contract") if isinstance(handler_result.get("delivery_contract"), dict) else {}
    artifacts = delivery_contract.get("artifacts") if isinstance(delivery_contract.get("artifacts"), list) else []
    deployment_record = None
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "deployment_record":
            deployment_record = artifact
    if deployment_record:
        content = deployment_record.get("content") if isinstance(deployment_record.get("content"), dict) else {}
        service_name = content.get("service_name")
        if service_name:
            return {
                "found": True,
                "deployed": True,
                "service_name": service_name,
                "region": content.get("region") or DEFAULT_REGION,
                "project_id": content.get("project_id"),
                "service_url": content.get("service_url"),
                "application_name": context.get("application_name"),
                "workspace_owner_id": context.get("workspace_owner_id"),
            }

    service_name = context.get("service_name")
    if service_name:
        return {
            "found": True,
            "deployed": False,
            "service_name": service_name,
            "region": DEFAULT_REGION,
            "project_id": None,
            "service_url": None,
            "application_name": context.get("application_name"),
            "workspace_owner_id": context.get("workspace_owner_id"),
        }

    return {"found": False, "reason": "no_deployment_identity_recorded", "workspace_owner_id": context.get("workspace_owner_id")}


def delete_saas_builder_project_records(db: Session, *, workflow_run_id: str) -> Dict[str, Any]:
    """Delete every DB row for a saas_builder project - PlatformWorkflowStepRun children
    first, then the PlatformWorkflowRun row, plus a defensive sweep of every other
    project_id-keyed table (see _PROJECT_ID_KEYED_MODELS). Returns a real per-table row-count
    report, computed before deletion so it can be printed as a before-report by the caller.
    """
    report: Dict[str, int] = {}

    step_rows = db.query(PlatformWorkflowStepRun).filter(PlatformWorkflowStepRun.workflow_run_id == workflow_run_id).all()
    report["platform_workflow_step_runs"] = len(step_rows)
    for row in step_rows:
        db.delete(row)

    run_rows = db.query(PlatformWorkflowRun).filter(PlatformWorkflowRun.workflow_run_id == workflow_run_id).all()
    report["platform_workflow_runs"] = len(run_rows)
    for row in run_rows:
        db.delete(row)

    for model in _PROJECT_ID_KEYED_MODELS:
        rows = db.query(model).filter(model.project_id == workflow_run_id).all()
        report[model.__tablename__] = len(rows)
        for row in rows:
            db.delete(row)

    db.commit()
    return {"deleted": True, "workflow_run_id": workflow_run_id, "row_counts": report}
