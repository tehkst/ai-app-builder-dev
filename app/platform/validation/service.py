from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.execution_migrations import run_execution_layer_migrations
from app.platform.persistence.models import PlatformValidationMission, PlatformValidationStep
from app.platform.validation.catalogue import validation_catalogue
from app.platform.validation.engine import execute_validation_mission, validation_mission_status


def build_validation_summary() -> Dict[str, Any]:
    run_execution_layer_migrations()
    with PlatformSessionLocal() as db:
        recent = db.query(PlatformValidationMission).order_by(PlatformValidationMission.id.desc()).limit(20).all()
    acceptance = build_acceptance_report()
    return {
        "status": "platform-validation-ready",
        "contract": "platform-validation-v1",
        "architectural_principle": "Implementation != Validation != Acceptance",
        "catalogue": validation_catalogue(),
        "recent_missions": [_mission_summary(item) for item in recent],
        "acceptance": acceptance,
    }


def run_validation_mission(payload: Dict[str, Any]) -> Dict[str, Any]:
    return execute_validation_mission(payload)


def get_validation_mission(payload: Dict[str, Any]) -> Dict[str, Any]:
    return validation_mission_status(str(payload.get("validation_mission_id") or ""))


def build_acceptance_report(payload: Dict[str, Any] = None) -> Dict[str, Any]:
    del payload
    run_execution_layer_migrations()
    rows: List[Dict[str, Any]] = []
    with PlatformSessionLocal() as db:
        for definition in validation_catalogue():
            validation_type = definition["validation_type"]
            mission = db.query(PlatformValidationMission).filter_by(
                validation_type=validation_type, execution_mode="live",
            ).order_by(PlatformValidationMission.id.desc()).first()
            rows.append(_acceptance_row(validation_type, definition["capabilities"], mission, db))
    passed = bool(rows) and all(row["status"] == "pass" for row in rows)
    return {
        "status": "pass" if passed else "unknown" if all(row["status"] == "unknown" for row in rows) else "fail",
        "accepted": passed,
        "authority": "durable-runtime-evidence",
        "evaluated_at": _now(),
        "missions": rows,
        "unknown_reason": None if passed else "Every catalogue mission requires a complete successful live validation run.",
    }


def latest_capability_validation(capability: str) -> Dict[str, Any]:
    run_execution_layer_migrations()
    with PlatformSessionLocal() as db:
        step = db.query(PlatformValidationStep).join(
            PlatformValidationMission,
            PlatformValidationMission.validation_mission_id == PlatformValidationStep.validation_mission_id,
        ).filter(
            PlatformValidationStep.capability == capability,
            PlatformValidationMission.execution_mode == "live",
        ).order_by(PlatformValidationStep.id.desc()).first()
        if not step:
            return {"status": "unknown", "runtime_verified": False, "unknown_reason": "No live validation evidence exists."}
        verification = _loads(step.verification_json, {})
        passed = step.status == "passed" and verification.get("acceptance_eligible") is True
        return {
            "status": "pass" if passed else "fail", "runtime_verified": passed,
            "execution_id": step.execution_id, "validation_mission_id": step.validation_mission_id,
            "evidence_id": step.evidence_id, "observed_at": step.completed_at.isoformat() if step.completed_at else step.started_at.isoformat(),
            "unknown_reason": None,
        }


def _acceptance_row(validation_type: str, capabilities: List[str], mission: Any, db: Any) -> Dict[str, Any]:
    if not mission:
        return {"validation_type": validation_type, "status": "unknown", "validation_mission_id": None, "capabilities": capabilities, "unknown_reason": "No live validation mission has run."}
    steps = db.query(PlatformValidationStep).filter_by(validation_mission_id=mission.validation_mission_id).all()
    passed = mission.final_result == "pass" and {step.capability for step in steps if step.status == "passed"} == set(capabilities)
    return {
        "validation_type": validation_type, "status": "pass" if passed else "fail",
        "validation_mission_id": mission.validation_mission_id, "capabilities": capabilities,
        "completed_at": mission.completed_at.isoformat() if mission.completed_at else None,
        "unknown_reason": None,
    }


def _mission_summary(mission: PlatformValidationMission) -> Dict[str, Any]:
    return {"validation_mission_id": mission.validation_mission_id, "mission_id": mission.mission_id, "validation_type": mission.validation_type, "execution_mode": mission.execution_mode, "status": mission.status, "final_result": mission.final_result, "completed_at": mission.completed_at.isoformat() if mission.completed_at else None}


def _loads(value: str, fallback: Any) -> Any:
    import json
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
