from __future__ import annotations

from typing import Any

from app.platform.operating_console.delivery_contract import add_existing_artifact, advance_contract
from app.platform.saas_builder.specification import bounded_specification
from app.platform.saas_builder.template import reference_file_changes, validation_plan


def prepare_reference_application(state: dict[str, Any]) -> dict[str, Any]:
    context = state["context"]
    spec = bounded_specification(context["founder_request"], context["application_name"])
    contract = state["delivery_contract"]
    specification = add_existing_artifact(
        state=state, artifact_type="application_specification",
        authority="saas_builder.specification", content=spec,
        source_references=list(contract.get("accepted_decision_references") or []),
        evidence_references=[],
    )
    contract["product_definition_reference"] = specification["artifact_id"]
    advance_contract(contract, "product_definition")
    architecture = add_existing_artifact(
        state=state, artifact_type="architecture_decision",
        authority="architecture_agent.reference_architecture",
        content={
            "status": "validated", "stack": ["FastAPI", "server-rendered HTML", "PostgreSQL", "Cloud Run"],
            "template": "appointment_booking_v1", "repository_strategy": "canonical multi-application repository",
            "source_directory": context["source_directory"], "service_name": context["service_name"],
        },
        source_references=[specification["artifact_id"]], evidence_references=["appointment_booking_v1"],
    )
    advance_contract(contract, "architecture")
    engineering = add_existing_artifact(
        state=state, artifact_type="engineering_plan", authority="engineering_manager",
        content={
            "mission_id": state["mission_id"], "specification_id": specification["artifact_id"],
            "template": "appointment_booking_v1", "validation_plan": validation_plan(context["application_id"]),
            "affected_files": [item["path"] for item in reference_file_changes(context["application_id"], spec)],
        },
        source_references=[specification["artifact_id"], architecture["artifact_id"]], evidence_references=[],
    )
    advance_contract(contract, "engineering_plan")
    files = reference_file_changes(context["application_id"], spec)
    change_set = {
        "change_set_status": "change_set_ready",
        "change_set_id": "SAAS-%s" % context["application_id"],
        "mission_id": state["mission_id"], "workflow_run_id": state["workflow_run_id"],
        "application_id": context["application_id"], "files": files,
        "validation": {"status": "contract-validated", "commands": validation_plan(context["application_id"])},
        "implementation_authority": "canonical-reference-template-assembler",
        "specification_reference": specification["artifact_id"],
        "provider": context["provider"], "model": context["model"],
    }
    add_existing_artifact(
        state=state, artifact_type="change_set",
        authority="canonical-reference-template-assembler", content=change_set,
        source_references=[engineering["artifact_id"]], evidence_references=[change_set["change_set_id"]],
    )
    contract["validation_evidence_references"].append(change_set["change_set_id"])
    advance_contract(contract, "implementation")
    advance_contract(contract, "repository_approval", next_governed_action={
        "capability": "github.repository_mutation", "authority": "governance_authorization",
        "approval_required": True,
    })
    state["specification"] = spec
    state["change_set"] = change_set
    state["status"] = "change_set_ready"
    state["current_stage"] = "change_set_ready"
    return {"success": True, "stage": "change_set_ready"}
